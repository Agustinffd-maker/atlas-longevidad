"""Composición local de planes de lectura; abrir estas rutas no consulta proveedores."""
from journal_guide import JOURNAL_GUIDE
from journal_metrics import registry
from radar_sources import SOURCE_REGISTRY, external_search_links
from research_profile import load_profile, build_research_queries, get_concept_suggestions


def radar_metadata():
    metrics = registry()
    guide = dict(JOURNAL_GUIDE, journals=metrics['journals'])
    return {
        'sources': SOURCE_REGISTRY,
        'journal_metrics': metrics,
        'journal_guide': guide,
        'limitations': [
            'Los índices pueden contener los mismos artículos: no son replicaciones independientes.',
            'Novedad significa una fecha dentro del período consultado, no una conclusión validada.',
            'No se combinan patentes, preprints, registros de ensayos y artículos en una puntuación de calidad.',
            'Máximo 12 registros por fuente; no es vigilancia exhaustiva ni una revisión sistemática.',
        ],
        'cache_hours': 6,
        'refresh_interval_hours': 6,
    }


def research_plan(path, query=None):
    profile = load_profile(path)
    longevity = build_research_queries(profile, scope='longevity')
    base_query = longevity[0]['query'] if longevity else '(longevity OR aging OR ageing OR healthspan)'
    queries = build_research_queries(profile, scope='thesis')
    bridges = build_research_queries(profile, scope='combined')
    selected = query or (bridges[0]['query'] if bridges else base_query)
    links = external_search_links(selected)
    return {
        'profile': profile,
        'queries': queries,
        'bridges': bridges,
        'longevity_query': base_query,
        'suggestions': get_concept_suggestions(profile.get('concepts', [])),
        'patent_links': links['patent_links'],
        'social_links': links['social_links'],
        'sources': SOURCE_REGISTRY,
        'relation_note': 'Los puentes y sugerencias son estrategias de búsqueda. Coincidir por términos no demuestra un mecanismo ni una mejora de longevidad.',
    }
