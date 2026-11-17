"""Datos sintéticos de QA; ninguna consulta de estos tests sale a internet."""
import json
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cache import EvidenceCache
from radar_service import RadarService, validate_radar_params


def synthetic_result(provider, query, start, end, **kwargs):
    return dict(items=[dict(id='SYNTHETIC-QA', title='SYNTHETIC TEST: not scientific evidence',
                           url='https://pubmed.ncbi.nlm.nih.gov/999999999/', kind='paper')],
                total=1, query=query, provider=provider, date_basis='Synthetic test date')


class RadarServiceTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.path = Path(self.folder.name) / 'radar.json'
        self.cache = EvidenceCache(self.path, 21600, records_key='items')
        self.params = validate_radar_params({'q': 'PUBLIC SYNTHETIC TEST'})

    def tearDown(self):
        self.folder.cleanup()

    def test_invalid_query_provider_and_dates(self):
        for value in ({'q': 4}, {'q': 'x'}, {'q': 'a'*1001}, {'q': 'a\nb'},
                      {'q': 'test', 'provider': 'https://other.example'},
                      {'q': 'test', 'end': '9999-01-01'},
                      {'q': 'test', 'start': 'yesterday'},
                      {'q': 'test', 'start': '2024-01-01', 'end': '2023-01-01'}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_radar_params(value)
        self.assertEqual(len(validate_radar_params({'q': 'a'*1000})['q']), 1000)

    def test_fresh_cache_avoids_network_and_preserves_source_semantics(self):
        calls = []
        def search(*args, **kwargs):
            calls.append(args)
            return synthetic_result(*args, **kwargs)
        service = RadarService(self.cache, search=search)
        first = service.search(self.params)
        second = service.search(self.params)
        self.assertEqual(len(calls), 1)
        self.assertTrue(second['cached'])
        self.assertEqual(first['fetched_at'], second['fetched_at'])
        self.assertEqual(second['date_basis'], 'Synthetic test date')
        reloaded = EvidenceCache(self.path, records_key='items')
        self.assertEqual(reloaded.get(self.params)['items'], first['items'])
        self.assertIsNone(EvidenceCache(self.path).get(self.params))

    def test_failure_retains_original_results_and_timestamp(self):
        first = RadarService(self.cache, search=synthetic_result).search(self.params)
        old_date = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
        self.cache.put(self.params, dict(first, fetched_at=old_date))
        def unavailable(*args, **kwargs):
            raise OSError('TEST OFFLINE')
        result = RadarService(self.cache, search=unavailable).search(self.params)
        self.assertTrue(result['stale'])
        self.assertTrue(result['error'])
        self.assertEqual(result['items'], first['items'])
        self.assertEqual(result['fetched_at'], old_date)
        self.assertEqual(self.cache.get(self.params)['fetched_at'], old_date)

    def test_failure_without_cache_invents_no_results_or_timestamp(self):
        def malformed(*args, **kwargs):
            return {'items': [None]}
        result = RadarService(self.cache, search=malformed).search(self.params)
        self.assertEqual(result['items'], [])
        self.assertIsNone(result['fetched_at'])
        self.assertFalse(self.path.exists())

    def test_cache_results_and_query_are_written_with_private_permissions(self):
        RadarService(self.cache, search=synthetic_result).search(self.params)
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)

    def test_force_is_rate_limited_and_clear_revokes_pending_refresh(self):
        calls = []
        def search(*args, **kwargs):
            calls.append(args)
            return synthetic_result(*args, **kwargs)
        service = RadarService(self.cache, search=search)
        service.search(self.params)
        service.search(self.params, force=True)
        self.assertEqual(len(calls), 1)
        generation = service.generation
        service.clear()
        self.assertIsNone(service.search(self.params, expected_generation=generation))
        self.assertEqual(self.cache.parameters(), [])
        self.assertFalse(self.path.exists())
        service.refresh_saved(threading.Event())
        self.assertEqual(len(calls), 1)
        service.search(self.params)
        self.assertEqual(len(calls), 2)
