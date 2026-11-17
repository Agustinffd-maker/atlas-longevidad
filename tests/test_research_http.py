"""Contrato HTTP local con fuentes controladas; perfil real en directorio temporal."""
import http.client
import json
import tempfile
import threading
import unittest
from unittest.mock import Mock
from http.server import ThreadingHTTPServer
from pathlib import Path

from cache import EvidenceCache
from sources import EvidenceService
from radar_service import RadarService
from server import make_handler
from test_app import FakeClient
from test_radar_service import synthetic_result


class ResearchHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory()
        root = Path(cls.folder.name)
        cls.profile = root / 'profile.json'
        cls.radar = RadarService(EvidenceCache(root / 'radar.json', records_key='items'), search=synthetic_result)
        service = EvidenceService(EvidenceCache(root / 'evidence.json'), FakeClient())
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), make_handler(service, cls.radar, cls.profile))
        cls.worker = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.worker.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.worker.join(timeout=2)
        cls.folder.cleanup()

    def request(self, path, method='GET', body=None, headers=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        connection.request(method, path, body=json.dumps(body) if body is not None else None,
                           headers=headers or {})
        response = connection.getresponse()
        result = json.loads(response.read())
        status = response.status
        self.assertEqual(response.getheader('Cache-Control'), 'no-store')
        connection.close()
        return status, result

    def setUp(self):
        self.profile.unlink(missing_ok=True)
        self.radar.clear()

    def test_metadata_and_disabled_plan_make_no_source_request(self):
        status, meta = self.request('/api/radar/meta')
        self.assertEqual(status, 200)
        self.assertEqual(len([s for s in meta['sources'] if s['automatic']]), 5)
        self.assertIn('quartiles', meta['journal_guide'])
        status, plan = self.request('/api/research-plan')
        self.assertFalse(plan['profile']['enabled'])
        self.assertEqual(plan['queries'], [])
        self.assertTrue(plan['patent_links'] and plan['social_links'])
        self.assertEqual(self.radar.cache.parameters(), [])

    def test_profile_roundtrip_does_not_send_title_and_delete_clears_radar(self):
        headers = {'Content-Type': 'application/json', 'X-Local-Request': '1'}
        status, profile = self.request('/api/profile', 'POST', {
            'enabled': True, 'title': 'SYNTHETIC LOCAL LABEL', 'concepts': ['RNA splicing']}, headers)
        self.assertEqual(status, 200)
        status, plan = self.request('/api/research-plan')
        self.assertTrue(plan['profile']['enabled'])
        self.assertNotIn('SYNTHETIC LOCAL LABEL', json.dumps(plan['queries'] + plan['bridges'] + plan['patent_links']))
        self.assertEqual(self.radar.cache.parameters(), [])
        self.assertEqual(self.request('/api/radar?q=PUBLIC-TEST')[0], 200)
        self.assertEqual(len(self.radar.cache.parameters()), 1)
        status, _ = self.request('/api/profile', 'DELETE', headers=headers)
        self.assertEqual(status, 200)
        self.assertFalse(self.profile.exists())
        self.assertEqual(self.radar.cache.parameters(), [])

    def test_profile_mutations_require_local_origin_and_header(self):
        for method in ('POST', 'DELETE'):
            self.assertEqual(self.request('/api/profile', method, {})[0], 403)
            self.assertEqual(self.request('/api/profile', method, {}, {'X-Local-Request': '1', 'Origin': 'https://other.example'})[0], 403)
        headers = {'X-Local-Request': '1'}
        self.assertEqual(self.request('/api/profile', 'POST', {'enabled': 'yes'}, headers)[0], 400)
        self.assertEqual(self.request('/api/radar?provider=untrusted&q=test')[0], 400)
        self.assertEqual(self.request('/api/research-plan?q=x')[0], 400)

    def test_cancelled_client_does_not_raise_while_sending_headers_or_body(self):
        for stage in ('headers', 'body'):
            with self.subTest(stage=stage):
                handler = object.__new__(self.server.RequestHandlerClass)
                handler.send_response = Mock()
                handler.send_header = Mock()
                handler.end_headers = Mock(side_effect=ConnectionResetError() if stage == 'headers' else None)
                handler.wfile = Mock()
                handler.wfile.write.side_effect = BrokenPipeError() if stage == 'body' else None
                handler.send(200, {'test': 'SYNTHETIC PUBLIC RESPONSE'})
                handler.send_response.assert_called_once_with(200)
