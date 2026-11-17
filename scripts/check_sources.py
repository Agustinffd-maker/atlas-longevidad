#!/usr/bin/env python3
"""Integración real optativa; nunca usa fixtures ni necesita credenciales."""
import json
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sources import NCBI, OfficialClient, parse_pubmed, pubmed_search, europe_search, validate_params


def main():
    client = OfficialClient()
    params = validate_params({"q": '"artificial intelligence" AND medicine', "start": "2023-01-01"})
    for name, search in (("PubMed", pubmed_search), ("Europe PMC", europe_search)):
        articles, total = search(params, client)
        assert articles and articles[0]["pmid"].isdigit(), name + " no devolvió fuentes"
        print(json.dumps({"source": name, "total": total, "returned": len(articles), "first_pmid": articles[0]["pmid"], "first_title": articles[0]["title"], "fetched_at": articles[0]["fetched_at"]}, ensure_ascii=False))
    if "--write-seed" in sys.argv:
        ids = list(json.loads((ROOT / 'data/reference_seed.json').read_text(encoding='utf-8')))
        raw = client.fetch(NCBI + "efetch.fcgi?" + urllib.parse.urlencode(dict(db="pubmed", id=",".join(ids), retmode="xml", tool="biomarcadores_local")))
        articles = parse_pubmed(raw)
        assert set(ids) == {item["pmid"] for item in articles}
        target = ROOT / "data/reference_seed.json"
        target.parent.mkdir(exist_ok=True)
        seed = {}
        for item in articles:
            public = {key: value for key, value in item.items() if key != 'abstract'}
            public['abstract_available'] = bool(item.get('abstract'))
            public['access'] = 'Metadatos; resumen en la fuente' if public['abstract_available'] else 'Metadatos; sin resumen en el registro'
            seed[item['pmid']] = public
        target.write_text(json.dumps(seed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        for item in articles:
            print(item["pmid"], item["title"], item["published"])


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError) as exc:
        print("No se completó la comprobación de una fuente (" + type(exc).__name__ + "). Revisa la conexión y reintenta más tarde.", file=sys.stderr)
        raise SystemExit(1)
