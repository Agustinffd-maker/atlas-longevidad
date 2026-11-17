"""Perfil de investigación local y propuestas de búsqueda; ninguna función consulta internet."""
import json
import os
import tempfile
import threading
import unicodedata
from datetime import datetime
from pathlib import Path

from cache import now_iso

SCHEMA_VERSION = 1
MAX_CONCEPTS = 6
MAX_QUERY_LENGTH = 1000
STARTER_CONCEPTS = ['modelos fundacionales biomédicos', 'IA multimodal', 'célula virtual']
LONGEVITY_QUERY = '(longevity OR aging OR ageing OR healthspan)'
_LOCK = threading.RLock()
_DATA_PATH = Path(__file__).resolve().parent / 'data/research_concepts.json'


def default_profile():
    return dict(schema_version=SCHEMA_VERSION, enabled=False, title='', concepts=[],
                synonyms={}, updated_at=None)


def _text(value, label, minimum=0, maximum=80, query_term=True):
    if not isinstance(value, str) or any(ord(char) < 32 for char in value):
        raise ValueError(label + ' debe ser texto sin saltos de línea ni controles.')
    value = ' '.join(value.strip().split())
    if not minimum <= len(value) <= maximum:
        raise ValueError(label + ' debe tener entre ' + str(minimum) + ' y ' + str(maximum) + ' caracteres.')
    if query_term and ('"' in value or '\\' in value):
        raise ValueError(label + ' debe ser un término simple, sin comillas dobles ni barras inversas.')
    return value


def _key(value):
    return ''.join(char for char in unicodedata.normalize('NFKD', value.casefold())
                   if not unicodedata.combining(char))


def validate_profile(values):
    """Normalizar la configuración sin habilitarla implícitamente ni generar consultas externas."""
    if not isinstance(values, dict):
        raise ValueError('El perfil de investigación debe ser un objeto JSON.')
    version = values.get('schema_version', SCHEMA_VERSION)
    if type(version) is not int or version != SCHEMA_VERSION:
        raise ValueError('Versión de perfil no compatible.')
    enabled = values.get('enabled', False)
    if not isinstance(enabled, bool):
        raise ValueError('La activación del módulo debe ser verdadera o falsa.')
    title = _text(values.get('title', ''), 'El título', maximum=100, query_term=False)
    raw_concepts = values.get('concepts', [])
    if not isinstance(raw_concepts, list) or len(raw_concepts) > MAX_CONCEPTS:
        raise ValueError('Selecciona hasta seis conceptos de investigación.')
    concepts = [_text(item, 'Cada concepto', 2, 80) for item in raw_concepts]
    if len({_key(item) for item in concepts}) != len(concepts):
        raise ValueError('No repitas conceptos; añade sus variantes como sinónimos.')
    if enabled and not concepts:
        raise ValueError('Añade al menos un concepto antes de activar el módulo de investigación.')
    raw_synonyms = values.get('synonyms', {})
    if not isinstance(raw_synonyms, dict) or not set(raw_synonyms) <= set(concepts):
        raise ValueError('Los sinónimos deben corresponder a conceptos guardados.')
    synonyms = {}
    for concept, variants in raw_synonyms.items():
        if not isinstance(variants, list) or len(variants) > 5:
            raise ValueError('Usa hasta cinco variantes por concepto.')
        clean, seen = [], {_key(concept)}
        for variant in variants:
            value = _text(variant, 'Cada variante', 2, 80)
            if _key(value) not in seen:
                clean.append(value)
                seen.add(_key(value))
        if clean:
            synonyms[concept] = clean
    updated_at = values.get('updated_at')
    if updated_at is not None:
        if not isinstance(updated_at, str) or len(updated_at) > 40:
            raise ValueError('Fecha del perfil inválida.')
        try:
            parsed = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
            if parsed.tzinfo is None:
                raise ValueError()
        except ValueError:
            raise ValueError('Fecha del perfil inválida.')
    return dict(schema_version=SCHEMA_VERSION, enabled=enabled, title=title,
                concepts=concepts, synonyms=synonyms, updated_at=updated_at)


def load_profile(path):
    with _LOCK:
        try:
            return validate_profile(json.loads(Path(path).read_text(encoding='utf-8')))
        except FileNotFoundError:
            return default_profile()
        except (OSError, ValueError, TypeError):
            profile = default_profile()
            profile['storage_warning'] = 'No se pudo leer el perfil local. El módulo está desactivado; revisa o guarda de nuevo la configuración.'
            return profile


def save_profile(path, values):
    """Escritura atómica con archivo privado; un fallo no sustituye el perfil válido anterior."""
    profile = validate_profile(values)
    profile['updated_at'] = now_iso()
    path = Path(path)
    with _LOCK:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                             prefix=path.stem + '-', suffix='.tmp', delete=False) as target:
                temporary = Path(target.name)
                json.dump(profile, target, ensure_ascii=False, indent=2)
                target.flush()
                os.fsync(target.fileno())
            os.replace(temporary, path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    return profile


def delete_profile(path):
    with _LOCK:
        Path(path).unlink(missing_ok=True)
    return default_profile()


def concept_catalog():
    return json.loads(_DATA_PATH.read_text(encoding='utf-8'))


def _matching_concept(term, nodes):
    target = _key(term)
    for node in nodes:
        if target in {_key(value) for value in [node['term'], node['label']] + node['aliases']}:
            return node
    return None


def get_concept_suggestions(concepts):
    """Sugerencias editoriales explícitas; no son una inferencia causal ni se autoañaden."""
    normalized = validate_profile({'concepts': concepts})['concepts']
    data = concept_catalog()
    nodes = data['concepts']
    by_id = {node['id']: node for node in nodes}
    selected_nodes = {_matching_concept(term, nodes)['id'] for term in normalized
                      if _matching_concept(term, nodes)}
    suggestions, seen = [], set()
    def append(node_id, relation_type, reason, selected_from):
        node = by_id[node_id]
        if node_id in seen or node_id in selected_nodes:
            return
        seen.add(node_id)
        suggestions.append(dict(term=node['term'], label=node['label'], reason=reason,
                                relation_type=relation_type, source_url=node['source_url'],
                                source_label=node['source_label'], selected_from=selected_from,
                                relation_note=data['relation_note']))
    for concept in normalized:
        match = _matching_concept(concept, nodes)
        if match:
            for related in match['related']:
                append(related['id'], related['relation_type'], related['reason'], concept)
    if not suggestions:
        for node_id in data['fallback_concepts']:
            append(node_id, 'method', 'Ayuda a revisar medición, modelo y reproducibilidad en una búsqueda nueva; no presupone relación biológica con tu tema.', 'Estrategia de búsqueda')
    return suggestions[:12]


def _query_group(concept, variants, nodes, budget):
    match = _matching_concept(concept, nodes)
    candidates = [concept] + variants + (match['search_terms'] if match else [])
    selected, seen = [], set()
    for term in candidates:
        if _key(term) in seen:
            continue
        candidate = selected + ['"' + term + '"']
        if len('(' + ' OR '.join(candidate) + ')') <= budget:
            selected = candidate
            seen.add(_key(term))
    return '(' + ' OR '.join(selected) + ')', len(selected), len({_key(term) for term in candidates})


def build_research_queries(profile, scope='longevity'):
    """Vista previa de consultas independientes; no busca ni configura un temporizador."""
    if scope not in {'longevity', 'thesis', 'combined'}:
        raise ValueError('Ámbito de actualización no reconocido.')
    data = concept_catalog()
    if scope == 'longevity':
        queries = [dict(label='Longevidad y envejecimiento', query=LONGEVITY_QUERY,
                        concepts=['longevity', 'aging', 'healthspan'],
                        relation_note='Consulta general de actualidad. La coincidencia por términos no verifica relevancia ni eficacia.')]
        by_id = {node['id']: node for node in data['concepts']}
        for node_id in data['longevity_themes'][:5]:
            node = by_id[node_id]
            queries.append(dict(label=node['label'] + ' y longevidad',
                                query=LONGEVITY_QUERY + ' AND "' + node['term'] + '"',
                                concepts=[node['term']], relation_note=data['relation_note']))
        return queries
    checked = validate_profile(profile)
    if not checked['enabled']:
        return []
    queries = []
    prefix = LONGEVITY_QUERY + ' AND ' if scope == 'combined' else ''
    for concept in checked['concepts']:
        group, used, available = _query_group(concept, checked['synonyms'].get(concept, []),
                                             data['concepts'], MAX_QUERY_LENGTH - len(prefix))
        note = ('Intersección de términos para buscar un posible puente con longevidad; no prueba una relación.'
                if scope == 'combined' else 'Seguimiento del concepto de investigación; no exige que todos los temas aparezcan juntos.')
        if used < available:
            note += ' Se muestran ' + str(used) + ' de ' + str(available) + ' variantes por el límite de la consulta; puedes revisar o acotar tus términos.'
        queries.append(dict(label=concept + (' y longevidad' if scope == 'combined' else ''),
                            query=prefix + group, concepts=[concept], relation_note=note))
    return queries
