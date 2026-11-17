"""Consultas explícitas del radar: caché, procedencia y recuperación por fuente."""
import threading
import time
import xml.etree.ElementTree as ET
from datetime import date, timedelta

from cache import now_iso
from sources import OfficialClient
from radar_sources import PROVIDERS, search_provider


def validate_radar_params(values):
    if not isinstance(values, dict):
        raise ValueError('La consulta debe ser un objeto JSON.')
    for key in ('q', 'provider', 'start', 'end'):
        if key in values and not isinstance(values[key], str):
            raise ValueError('Los campos de búsqueda deben ser texto.')
    query = values.get('q', '').strip()
    if not 2 <= len(query) <= 1000 or any(ord(char) < 32 for char in query):
        raise ValueError('Usa una consulta pública de 2 a 1000 caracteres, en una sola línea.')
    provider = values.get('provider', 'pubmed')
    if provider not in PROVIDERS:
        raise ValueError('Fuente de radar no reconocida.')
    today = date.today()
    try:
        start = date.fromisoformat(values.get('start', (today - timedelta(days=90)).isoformat()))
        end = date.fromisoformat(values.get('end', today.isoformat()))
    except (TypeError, ValueError):
        raise ValueError('Las fechas deben tener formato AAAA-MM-DD.')
    if start.year < 1900 or start > end or end > today:
        raise ValueError('Revisa las fechas: desde 1900 hasta hoy, en orden.')
    return dict(q=query, provider=provider, start=start.isoformat(), end=end.isoformat())


class RadarService:
    def __init__(self, cache, client=None, search=None):
        self.cache = cache
        self.client = client or OfficialClient()
        self.search_source = search or search_provider
        self.lock = threading.RLock()
        self.attempts = {}
        self.generation = 0

    def clear(self):
        with self.lock:
            self.cache.clear()
            self.attempts = {}
            self.generation += 1

    def refresh_saved(self, stopped):
        generation = self.generation
        for params in self.cache.parameters():
            if stopped.is_set() or self.generation != generation:
                return
            self.search(params, expected_generation=generation)

    def search(self, values, force=False, expected_generation=None):
        params = validate_radar_params(values)
        with self.lock:
            if expected_generation is not None and expected_generation != self.generation:
                return None  # Un cambio de perfil revocó esta renovación pendiente.
            previous = self.cache.get(params)
            if previous and self.cache.fresh(previous) and not force:
                return dict(previous, cached=True, stale=False, error=None)
            key = self.cache.key(params)
            last = self.attempts.get(key)
            if last and time.monotonic() - last[0] < 60:
                return dict(last[1], cached=True)
            attempted_at = now_iso()
            try:
                result = self.search_source(params['provider'], params['q'], params['start'],
                                            params['end'], limit=12, client=self.client)
                if not isinstance(result, dict) or not isinstance(result.get('items'), list):
                    raise ValueError('Respuesta de radar inválida.')
                if len(result['items']) > 12 or any(not isinstance(item, dict) or not item.get('id') or
                        not isinstance(item.get('title'), str) or not isinstance(item.get('url'), str)
                        for item in result['items']):
                    raise ValueError('Registros de radar inválidos.')
                value = dict(result, query=params['q'], provider=params['provider'], fetched_at=now_iso(),
                             last_attempt_at=attempted_at, stale=False, cached=False, error=None)
                self.cache.put(params, value)
            except (OSError, ValueError, KeyError, TypeError, AttributeError, ET.ParseError):
                message = 'No se pudo consultar esta fuente. Revisa tu conexión y reintenta en un minuto.'
                value = dict(previous, cached=True, stale=True, error=message, last_attempt_at=attempted_at) if previous else dict(
                    items=[], total=None, query=params['q'], provider=params['provider'], fetched_at=None,
                    last_attempt_at=attempted_at, stale=True, cached=False, error=message)
            self.attempts[key] = (time.monotonic(), value)
            return value
