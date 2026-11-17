"""Cruce por ISSN con una instantánea histórica revisada; jamás inferir por prestigio."""
import json
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def registry():
    path = Path(__file__).resolve().parent / 'data/journal_metrics.json'
    return json.loads(path.read_text(encoding='utf-8'))


def enrich_article(article):
    result = dict(article)
    values = article.get('issns', [])
    issns = set(values) if isinstance(values, list) and all(isinstance(item, str) for item in values) else set()
    data = registry()
    matches = [journal for journal in data['journals'] if issns.intersection(journal['issns'])]
    if len(matches) != 1:
        result['quartile'] = 'cuartil no verificado'
        result.pop('quartile_details', None)
        return result
    match = matches[0]
    result['quartile'] = match['quartile']
    result['quartile_details'] = {key: value for key, value in data.items() if key != 'journals'}
    result['quartile_details'].update(match)
    result['quartile_details']['source_url'] += '#page=' + str(match['pdf_page'])
    return result
