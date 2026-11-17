"""Adaptadores oficiales. Metadatos y resúmenes son datos, no conclusiones."""
import json
import html
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date

from cache import now_iso
from journal_metrics import enrich_article

NCBI = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
EUROPE = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
KINDS = {"all", "review", "trial", "original"}
MODELS = {"all", "humans", "animals", "cells", "computational"}


def validate_params(values):
    if not isinstance(values, dict) or any(key in values and not isinstance(values[key], str) for key in ("q", "provider", "kind", "model", "start", "end")):
        raise ValueError("Los campos de búsqueda deben ser texto.")
    query = values.get("q", "").strip()
    if not 2 <= len(query) <= 250 or any(ord(c) < 32 for c in query):
        raise ValueError("Escribe una consulta pública de 2 a 250 caracteres.")
    provider = values.get("provider", "pubmed")
    kind, model = values.get("kind", "all"), values.get("model", "all")
    if provider not in {"pubmed", "europepmc"} or kind not in KINDS or model not in MODELS:
        raise ValueError("Fuente o filtro no reconocido.")
    start, end = values.get("start", "2000-01-01"), values.get("end", date.today().isoformat())
    try:
        first, last = date.fromisoformat(start), date.fromisoformat(end)
    except (ValueError, TypeError):
        raise ValueError("Las fechas deben tener formato AAAA-MM-DD.")
    if first > last or first.year < 1900 or last > date.today():
        raise ValueError("Revisa el intervalo de fechas (desde 1900 hasta hoy).")
    return dict(q=query, provider=provider, kind=kind, model=model, start=start, end=end)


class OfficialClient:
    def __init__(self):
        self.lock = threading.Lock()
        self.last_request = 0.0

    def fetch(self, url):
        # Global para ambos proveedores: <=2 solicitudes/segundo, sin clave.
        with self.lock:
            time.sleep(max(0, .5 - (time.monotonic() - self.last_request)))
            self.last_request = time.monotonic()
            request = urllib.request.Request(url, headers={"User-Agent": "BiomarcadoresLocal/1.0 (academic; NCBI E-utilities)"})
            with urllib.request.urlopen(request, timeout=18) as response:
                raw = response.read(5_000_001)
            if len(raw) > 5_000_000:
                raise ValueError("Respuesta demasiado grande.")
            return raw


def text_of(element):
    return "" if element is None else "".join(element.itertext()).strip()


def plain_markup(value):
    if not isinstance(value, str):
        raise ValueError("Se esperaba texto en el registro externo.")
    return re.sub(r"<[^>]+>", "", html.unescape(value)).strip()


def model_label(mesh, title, abstract):
    labels = []
    if "Humans" in mesh:
        labels.append("Humanos (MeSH)")
    if "Animals" in mesh:
        labels.append("Animales (MeSH)")
    if labels:
        return " · ".join(labels)
    raw = (title + " " + abstract).lower()
    if re.search(r"in vitro|cell culture|cultured cells", raw):
        return "Posible modelo celular (orientativo)"
    if re.search(r"computational|in silico|machine learning", raw):
        return "Posible modelo computacional (orientativo)"
    return "Modelo no determinado; revisar artículo"


def article_record(pmid, title, journal, published, doi, types, abstract, mesh, provider, precision="día", issns=None):
    if not re.fullmatch(r"\d{1,10}", str(pmid)) or not isinstance(title, str) or not title.strip():
        raise ValueError("Artículo sin PMID o título válido.")
    if not isinstance(types, list) or not all(isinstance(value, str) for value in types):
        raise ValueError("Tipos de publicación inválidos.")
    if not isinstance(abstract, str) or not isinstance(mesh, list) or not isinstance(journal, str):
        raise ValueError("Campos del registro científico inválidos.")
    if published is not None and not isinstance(published, str):
        raise ValueError("Fecha de publicación inválida.")
    if doi is not None and not isinstance(doi, str):
        raise ValueError("DOI inválido.")
    if doi and not re.fullmatch(r"10\.\d{4,9}/\S+", doi):
        doi = None
    result = dict(pmid=str(pmid), title=title, journal=journal or "Revista no informada",
                published=published or None, date_precision=precision, doi=doi,
                url="https://pubmed.ncbi.nlm.nih.gov/" + str(pmid) + "/",
                types=types or ["Tipo no informado"], model=model_label(mesh, title, abstract),
                abstract=abstract or None, access="Metadatos y resumen" if abstract else "Solo metadatos",
                provider=provider, quartile="cuartil no verificado", fetched_at=now_iso())
    result['issns'] = sorted({value for value in (issns or []) if isinstance(value, str) and re.fullmatch(r'\d{4}-\d{3}[\dXx]', value)})
    return enrich_article(result)


def parse_pubmed(raw):
    root = ET.fromstring(raw)
    if root.tag != "PubmedArticleSet":
        raise ValueError("Respuesta XML de PubMed inesperada.")
    articles = []
    for item in root.findall("PubmedArticle"):
        article = item.find("MedlineCitation/Article")
        if article is None:
            raise ValueError("Registro de PubMed incompleto.")
        published = article.find("ArticleDate")
        if published is None:
            published = article.find("Journal/JournalIssue/PubDate")
        year, month, day = (text_of(published.find(tag)) if published is not None else "" for tag in ("Year", "Month", "Day"))
        months = {name: str(i).zfill(2) for i, name in enumerate("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split(), 1)}
        month = months.get(month, month.zfill(2)) if month else ""
        stamp = "-".join(part for part in (year, month, day.zfill(2) if day else "") if part)
        if not year and published is not None:
            stamp = text_of(published.find("MedlineDate"))
        abstract = "\n\n".join((node.get("Label", "") + ": " if node.get("Label") else "") + text_of(node) for node in article.findall("Abstract/AbstractText"))
        doi = next((text_of(node) for node in item.findall("PubmedData/ArticleIdList/ArticleId") if node.get("IdType") == "doi"), None)
        articles.append(article_record(
            text_of(item.find("MedlineCitation/PMID")), text_of(article.find("ArticleTitle")),
            text_of(article.find("Journal/Title")), stamp, doi,
            [text_of(node) for node in article.findall("PublicationTypeList/PublicationType")], abstract,
            [text_of(node) for node in item.findall("MedlineCitation/MeshHeadingList/MeshHeading/DescriptorName")],
            "pubmed", "día" if day else "mes" if month else "año o intervalo",
            issns=[text_of(article.find('Journal/ISSN')), text_of(item.find('MedlineCitation/MedlineJournalInfo/ISSNLinking'))]))
    return articles


def pubmed_search(params, client):
    term = "(" + params["q"] + ")"
    kinds = {"review": ' AND (Review[pt] OR Systematic Review[pt])', "trial": ' AND Clinical Trial[pt]', "original": ' NOT (Review[pt] OR Editorial[pt] OR Letter[pt])'}
    models = {"humans": ' AND Humans[mh]', "animals": ' AND Animals[mh]', "cells": ' AND ("in vitro"[tiab] OR "cell culture"[tiab])', "computational": ' AND ("in silico"[tiab] OR computational[tiab])'}
    term += kinds.get(params["kind"], "") + models.get(params["model"], "")
    args = dict(db="pubmed", term=term, retmode="json", retmax=20, sort="pub date", datetype="pdat", mindate=params["start"], maxdate=params["end"], tool="biomarcadores_local")
    search = json.loads(client.fetch(NCBI + "esearch.fcgi?" + urllib.parse.urlencode(args)))
    result = search["esearchresult"]
    if "error" in result or "ERROR" in search:
        raise ValueError("PubMed rechazó la consulta.")
    ids = result["idlist"]
    if not isinstance(ids, list) or any(not re.fullmatch(r"\d{1,10}", str(i)) for i in ids):
        raise ValueError("Lista de identificadores inválida.")
    if not ids:
        return [], int(result["count"])
    args = dict(db="pubmed", id=",".join(ids), retmode="xml", tool="biomarcadores_local")
    articles = parse_pubmed(client.fetch(NCBI + "efetch.fcgi?" + urllib.parse.urlencode(args)))
    if not articles:
        raise ValueError("PubMed devolvió IDs sin registros recuperables.")
    return articles, int(result["count"])


def europe_search(params, client):
    query = '(' + params['q'] + ') AND SRC:MED AND FIRST_PDATE:[' + params['start'] + ' TO ' + params['end'] + ']'
    kinds = {"review": ' AND PUB_TYPE:review', "trial": ' AND PUB_TYPE:"clinical trial"', "original": ' NOT (PUB_TYPE:review OR PUB_TYPE:editorial OR PUB_TYPE:letter)'}
    models = {"humans": ' AND MESH_HEADING:Humans', "animals": ' AND MESH_HEADING:Animals', "cells": ' AND ("in vitro" OR "cell culture")', "computational": ' AND ("in silico" OR computational)'}
    query += kinds.get(params["kind"], "") + models.get(params["model"], "") + " sort_date:y"
    args = dict(query=query, format="json", resultType="core", pageSize=20)
    data = json.loads(client.fetch(EUROPE + "?" + urllib.parse.urlencode(args)))
    if not isinstance(data, dict) or not isinstance(data.get("resultList"), dict) or not isinstance(data["resultList"].get("result"), list) or "hitCount" not in data:
        raise ValueError("Respuesta de Europe PMC inesperada.")
    articles = []
    for item in data["resultList"]["result"]:
        if not isinstance(item, dict) or not isinstance(item.get("journalInfo", {}), dict) or not isinstance(item.get("pubTypeList", {}), dict) or not isinstance(item.get("meshHeadingList", {}), dict):
            raise ValueError("Registro de Europe PMC malformado.")
        journal = item.get("journalInfo", {}).get("journal", {}).get("title", "")
        mesh = [node.get("descriptorName", "") for node in item.get("meshHeadingList", {}).get("meshHeading", [])]
        articles.append(article_record(item.get("pmid") or item.get("id", ""), plain_markup(item.get("title", "")), journal,
            item.get("firstPublicationDate") or item.get("pubYear"), item.get("doi"),
            item.get("pubTypeList", {}).get("pubType", []),
            plain_markup(item.get("abstractText", "")), mesh, "europepmc",
            issns=[item.get('journalInfo', {}).get('journal', {}).get('issn'), item.get('journalInfo', {}).get('journal', {}).get('essn')]))
    if int(data["hitCount"]) > 0 and not articles:
        raise ValueError("Europe PMC devolvió registros vacíos.")
    return articles, int(data["hitCount"])


class EvidenceService:
    def __init__(self, cache, client=None):
        self.cache = cache
        self.client = client or OfficialClient()
        self.lock = threading.RLock()
        self.attempts = {}

    def search(self, params, force=False):
        with self.lock:
            previous = self.cache.get(params)
            if previous and self.cache.fresh(previous) and not force:
                return dict(previous, cached=True, stale=False, error=None)
            key = self.cache.key(params)
            attempt = self.attempts.get(key)
            if attempt and time.monotonic() - attempt[0] < 60:
                if attempt[1] is not None:
                    return dict(attempt[1], cached=True)
            attempted_at = now_iso()
            try:
                search = pubmed_search if params["provider"] == "pubmed" else europe_search
                articles, total = search(params, self.client)
                value = dict(articles=articles, total=total, query=params["q"], provider=params["provider"],
                             fetched_at=now_iso(), last_attempt_at=attempted_at, stale=False, error=None, cached=False)
                self.cache.put(params, value)
            except (OSError, ValueError, KeyError, TypeError, AttributeError, ET.ParseError):
                # No registrar la consulta ni errores que puedan incluir URLs con parámetros.
                message = "No se pudo consultar la fuente. Revisa tu conexión y reintenta en un minuto."
                value = dict(previous, cached=True, stale=True, error=message, last_attempt_at=attempted_at) if previous else dict(
                    articles=[], total=None, query=params["q"], provider=params["provider"], fetched_at=None,
                    last_attempt_at=attempted_at, stale=True, error=message, cached=False)
            self.attempts[key] = (time.monotonic(), value)
            return value
