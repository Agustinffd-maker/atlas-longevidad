"""Fuentes del radar: registros trazables, nunca conclusiones o validación automática."""
import json
import re
from datetime import date
from pathlib import Path
from urllib.parse import quote, urlencode

from cache import now_iso
from journal_metrics import enrich_article
from sources import OfficialClient, EUROPE, europe_search, plain_markup, pubmed_search

SOURCE_REGISTRY = json.loads((Path(__file__).resolve().parent / 'data/radar_sources.json').read_text(encoding='utf-8'))['sources']
PROVIDERS = {source['id']: source for source in SOURCE_REGISTRY if source['automatic']}
CROSSREF = 'https://api.crossref.org/works'
TRIALS = 'https://clinicaltrials.gov/api/v2/studies'


def _text(value, required=False):
    if value is None and not required:
        return ''
    if not isinstance(value, str):
        raise ValueError('Se esperaba texto en la respuesta de la fuente.')
    value = plain_markup(value).strip()
    if required and not value:
        raise ValueError('Registro sin identificador o título.')
    return value


def _object(value):
    if not isinstance(value, dict):
        raise ValueError('Objeto externo malformado.')
    return value


def _strings(value):
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError('Lista de texto externa malformada.')
    return [_text(item) for item in value]


def _count(value):
    if isinstance(value, bool) or not (isinstance(value, int) or isinstance(value, str) and value.isdigit()):
        raise ValueError('Recuento de la fuente inválido.')
    number = int(value)
    if number < 0:
        raise ValueError('Recuento de la fuente negativo.')
    return number


def _doi(value):
    value = _text(value)
    return value if re.fullmatch(r'10\.\d{4,9}/\S+', value) else None


def _issns(values):
    return sorted({item.upper() for item in _strings(values) if re.fullmatch(r'\d{4}-\d{3}[\dXx]', item)})


def _partial_date(value):
    if value is None:
        return None
    text = _text(value)
    if not re.fullmatch(r'\d{4}(?:-\d{2}){0,2}', text):
        raise ValueError('Fecha externa inválida.')
    parts = [int(part) for part in text.split('-')]
    date(*(parts + [1] * (3 - len(parts))))
    return text


def _crossref_date(record):
    for key in ('published', 'published-online', 'published-print', 'issued'):
        if key not in record:
            continue
        parts = _object(record[key]).get('date-parts')
        if not isinstance(parts, list) or not parts or not isinstance(parts[0], list):
            raise ValueError('Fecha Crossref malformada.')
        values = parts[0]
        if not 1 <= len(values) <= 3 or any(type(value) is not int for value in values):
            raise ValueError('Precisión de fecha Crossref inválida.')
        return _partial_date('-'.join(str(value).zfill(4 if index == 0 else 2) for index, value in enumerate(values)))
    return None


def _record(provider, identifier, title, url, published, journal='', doi=None, pmid=None, summary=None,
            issns=None, evidence_status=None, **extra):
    source = PROVIDERS[provider]
    summary = _text(summary) or None
    item = dict(id=identifier, title=_text(title, required=True), url=url, doi=doi, pmid=pmid,
                published=published, journal=_text(journal), issns=issns or [], kind=source['kind'],
                evidence_status=evidence_status or 'Metadatos; estudio pendiente de evaluación crítica',
                summary=summary, source=provider, source_label=source['label'], source_url=url,
                metadata_only=summary is None, fetched_at=now_iso(), date_label=source['date_basis'],
                date_basis=source['date_basis'], query_semantics=source['query_semantics'],
                model='Modelo no determinado; revisar la fuente', flags=[])
    item.update(extra)
    if item['kind'] == 'paper':
        item = enrich_article(item)
    else:
        item['quartile'] = 'No aplica: ' + ('preprint' if item['kind'] == 'preprint' else 'registro de estudio')
    return item


def _bibliographic(provider, article):
    types = article.get('types', [])
    retracted = any('retracted publication' in item.lower() for item in types)
    notice = any('retraction of publication' in item.lower() for item in types)
    preprint = any(item.strip().lower() == 'preprint' for item in types)
    status = 'Publicación retractada según metadatos; no usar como respaldo' if retracted else (
        'Aviso de retractación según metadatos; revisar publicación afectada' if notice else
        'Preprint según metadatos; no se presume revisión por pares' if preprint else
        'Registro bibliográfico; revisión crítica y revisión por pares no comprobadas por el atlas')
    return _record(provider, article['pmid'], article['title'], article['url'], article['published'],
                   journal=article['journal'], doi=article.get('doi'), pmid=article['pmid'],
                   summary=article.get('abstract'), issns=article.get('issns', []), evidence_status=status,
                   model=article.get('model'), types=types,
                   kind='preprint' if preprint else 'paper',
                   flags=['retraction'] if retracted or notice else [])


def _preprints(query, start, end, limit, client):
    expression = f'({query}) AND SRC:PPR AND FIRST_PDATE:[{start} TO {end}] sort_date:y'
    data = _object(json.loads(client.fetch(EUROPE + '?' + urlencode(dict(
        query=expression, format='json', resultType='core', pageSize=limit)))))
    records = _object(data.get('resultList')).get('result')
    if not isinstance(records, list):
        raise ValueError('Lista de preprints inválida.')
    items = []
    for value in records[:limit]:
        value = _object(value)
        identifier = _text(value.get('id'), required=True)
        if value.get('source') != 'PPR' or not re.fullmatch(r'PPR\d{1,20}', identifier):
            raise ValueError('Registro no identificado como preprint PPR.')
        doi = _doi(value.get('doi'))
        items.append(_record('preprints', identifier, value.get('title'),
            'https://europepmc.org/article/PPR/' + identifier,
            _partial_date(value.get('firstPublicationDate') or value.get('pubYear')),
            doi=doi, summary=value.get('abstractText'), evidence_status='Preprint; no se presume revisión por pares',
            types=['Preprint']))
    return items, _count(data.get('hitCount'))


def _crossref(query, start, end, limit, client):
    # Crossref no es un motor booleano de PubMed. Se prioriza pertinencia dentro
    # de la ventana en lugar de traer lo más nuevo aunque sea de otro campo.
    args = {'query.bibliographic': query, 'filter': f'type:journal-article,from-pub-date:{start},until-pub-date:{end}',
            'sort': 'relevance', 'order': 'desc', 'rows': limit}
    data = _object(json.loads(client.fetch(CROSSREF + '?' + urlencode(args))))
    message = _object(data.get('message'))
    records = message.get('items')
    if not isinstance(records, list):
        raise ValueError('Lista Crossref inválida.')
    items = []
    for value in records[:limit]:
        value = _object(value)
        doi = _doi(value.get('DOI'))
        titles = _strings(value.get('title', []))
        journals = _strings(value.get('container-title', []))
        if not doi or not titles or value.get('type') != 'journal-article':
            raise ValueError('Artículo Crossref incompleto o tipo inesperado.')
        items.append(_record('crossref', doi.lower(), titles[0], 'https://doi.org/' + quote(doi, safe='/'),
            _crossref_date(value), journal=journals[0] if journals else '', doi=doi,
            summary=value.get('abstract'), issns=_issns(value.get('ISSN', [])), types=['journal-article'],
            evidence_status='Metadatos DOI del depositante; revisión por pares no comprobada'))
    return items, _count(message.get('total-results'))


def _trials(query, start, end, limit, client):
    args = {'query.term': f'({query}) AND AREA[LastUpdatePostDate]RANGE[{start},{end}]',
            'sort': 'LastUpdatePostDate:desc', 'pageSize': limit, 'countTotal': 'true', 'format': 'json',
            'fields': 'NCTId,BriefTitle,BriefSummary,OverallStatus,Phase,StudyType,EnrollmentCount,LastUpdatePostDate,StudyFirstPostDate,HasResults,Condition'}
    data = _object(json.loads(client.fetch(TRIALS + '?' + urlencode(args))))
    records = data.get('studies')
    if not isinstance(records, list):
        raise ValueError('Lista de estudios inválida.')
    items = []
    for value in records[:limit]:
        value = _object(value)
        protocol = _object(value.get('protocolSection'))
        identity = _object(protocol.get('identificationModule'))
        status = _object(protocol.get('statusModule'))
        design = _object(protocol.get('designModule', {}))
        identifier = _text(identity.get('nctId'), required=True)
        if not re.fullmatch(r'NCT\d{8}', identifier):
            raise ValueError('Identificador NCT inválido.')
        has_results = value.get('hasResults')
        if 'hasResults' in value and not isinstance(has_results, bool):
            raise ValueError('Indicador de resultados inválido.')
        posted = _object(status.get('lastUpdatePostDateStruct', {})).get('date')
        first_posted = _object(status.get('studyFirstPostDateStruct', {})).get('date')
        summary = _object(protocol.get('descriptionModule', {})).get('briefSummary')
        enrollment = _object(design.get('enrollmentInfo', {})).get('count')
        if enrollment is not None:
            enrollment = _count(enrollment)
        items.append(_record('trials', identifier, identity.get('briefTitle'),
            'https://clinicaltrials.gov/study/' + identifier, _partial_date(posted), summary=summary,
            evidence_status='Registro de estudio; no demuestra eficacia ni sustituye evaluar resultados',
            trial_phase=_strings(design.get('phases', [])), study_type=_text(design.get('studyType')),
            trial_status=_text(status.get('overallStatus')), has_results=has_results,
            enrollment=enrollment, first_posted=_partial_date(first_posted),
            conditions=_strings(_object(protocol.get('conditionsModule', {})).get('conditions', [])),
            model='Humanos: registro de estudio; revisar criterios de selección'))
    return items, _count(data.get('totalCount'))


def _validate(query, start, end, limit):
    if not isinstance(query, str) or not 2 <= len(query.strip()) <= 1000 or any(ord(c) < 32 for c in query):
        raise ValueError('Consulta pública de 2 a 1000 caracteres, sin caracteres de control.')
    if not isinstance(start, str) or not isinstance(end, str) or not all(
            re.fullmatch(r'\d{4}-\d{2}-\d{2}', value) for value in (start, end)):
        raise ValueError('Las fechas deben ser texto AAAA-MM-DD.')
    first, last = date.fromisoformat(start), date.fromisoformat(end)
    if first.year < 1900 or first > last or last > date.today():
        raise ValueError('Intervalo de fechas inválido.')
    if type(limit) is not int or not 1 <= limit <= 20:
        raise ValueError('El límite debe estar entre 1 y 20.')
    return query.strip()


def search_provider(provider, query, start, end, limit=12, client=None):
    """Consultar una fuente. Errores se propagan para que el servicio conserve su caché."""
    if not isinstance(provider, str) or provider not in PROVIDERS:
        raise ValueError('Fuente automática desconocida.')
    query = _validate(query, start, end, limit)
    client = client or OfficialClient()
    if provider in ('pubmed', 'europepmc'):
        params = dict(q=query, provider=provider, start=start, end=end, kind='all', model='all')
        function = pubmed_search if provider == 'pubmed' else europe_search
        articles, total = function(params, client)
        items = [_bibliographic(provider, article) for article in articles[:limit]]
    else:
        function = {'preprints': _preprints, 'crossref': _crossref, 'trials': _trials}[provider]
        items, total = function(query, start, end, limit, client)
    if total > 0 and not items:
        raise ValueError('La fuente informó coincidencias pero no entregó registros.')
    source = PROVIDERS[provider]
    return dict(items=items, total=total, query=query, provider=provider,
                date_basis=source['date_basis'], query_semantics=source['query_semantics'],
                limitations=source['limitations'])


def external_search_links(query):
    """Preparar búsquedas manuales sin contactar patentes, redes ni cuentas."""
    if not isinstance(query, str) or not 2 <= len(query.strip()) <= 1000 or any(ord(c) < 32 for c in query):
        raise ValueError('Consulta pública inválida.')
    query = query.strip()
    patents = []
    social = []
    for source in SOURCE_REGISTRY:
        if source['automatic']:
            continue
        item = dict(label=source['label'], url=source['search_url'], query=query,
                    scope=source['description'], note=source['limitations'],
                    automatic=False, prefilled=False, source=source['id'], docs_url=source['docs_url'])
        if source['id'] == 'patentscope':
            item['query'] = 'EN_ALL:(' + query + ')'
        if source['kind'] == 'social':
            item['url'] += '?' + urlencode({'q': query, 'sort': 'latest'})
            item['prefilled'] = True
            social.append(item)
        else:
            item['note'] += ' Copia la consulta al buscador oficial; verifica su sintaxis y fechas. No se han recuperado resultados.'
            patents.append(item)
    return dict(patent_links=patents, social_links=social)
