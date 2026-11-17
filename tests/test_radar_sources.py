"""Fixtures sintéticas del radar: prueban transporte/metadatos, no hallazgos."""
import copy
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from radar_sources import PROVIDERS, SOURCE_REGISTRY, external_search_links, search_provider
from test_app import FakeClient, XML_FIXTURE, METRICS_FIXTURE


PREPRINT = {'hitCount': 1, 'resultList': {'result': [{
    'id': 'PPR999999999', 'source': 'PPR', 'title': 'SYNTHETIC PREPRINT &lt;i&gt;aging&lt;/i&gt;',
    'doi': '10.9999/synthetic-preprint', 'firstPublicationDate': '2024-02-03',
    'abstractText': 'SYNTHETIC abstract; not scientific evidence.'
}]}}
CROSSREF = {'status': 'ok', 'message': {'total-results': 1, 'items': [{
    'DOI': '10.9999/SYNTHETIC-CROSSREF', 'type': 'journal-article',
    'title': ['SYNTHETIC ARTICLE'], 'container-title': ['SYNTHETIC JOURNAL'],
    'published': {'date-parts': [[2024, 2]]}, 'ISSN': ['1111-1111'],
    'abstract': '<jats:p>SYNTHETIC; not scientific evidence.</jats:p>'
}]}}
TRIAL = {'totalCount': 1, 'studies': [{
    'protocolSection': {
        'identificationModule': {'nctId': 'NCT99999999', 'briefTitle': 'SYNTHETIC STUDY'},
        'statusModule': {'overallStatus': 'RECRUITING',
                         'lastUpdatePostDateStruct': {'date': '2024-02-03'},
                         'studyFirstPostDateStruct': {'date': '2020-01-01'}},
        'descriptionModule': {'briefSummary': 'SYNTHETIC protocol, not results.'},
        'designModule': {'studyType': 'INTERVENTIONAL', 'phases': ['PHASE1'],
                         'enrollmentInfo': {'count': 20}},
        'conditionsModule': {'conditions': ['SYNTHETIC CONDITION']}
    }, 'hasResults': False
}]}


class RadarSourceTests(unittest.TestCase):
    def setUp(self):
        mocked = patch('journal_metrics.registry', return_value=METRICS_FIXTURE)
        mocked.start()
        self.addCleanup(mocked.stop)

    def search(self, provider, response):
        client = FakeClient(response)
        result = search_provider(provider, 'PUBLIC SYNTHETIC QUERY', '2024-01-01', '2024-12-31', 4, client)
        return result, client

    def test_only_approved_automatic_providers(self):
        self.assertEqual(set(PROVIDERS), {'pubmed', 'europepmc', 'preprints', 'crossref', 'trials'})
        self.assertEqual(len(SOURCE_REGISTRY), len({item['id'] for item in SOURCE_REGISTRY}))
        for item in SOURCE_REGISTRY:
            self.assertTrue(item['docs_url'].startswith('https://'))
            self.assertTrue(item['description'] and item['limitations'])

    def test_input_validation_precedes_network(self):
        client = FakeClient()
        for provider, query, start, end, limit in [
            ('unknown', 'test', '2024-01-01', '2024-12-31', 4),
            ([], 'test', '2024-01-01', '2024-12-31', 4),
            ('preprints', 'x', '2024-01-01', '2024-12-31', 4),
            ('preprints', 'a' * 1001, '2024-01-01', '2024-12-31', 4),
            ('preprints', 'x\ny', '2024-01-01', '2024-12-31', 4),
            ('preprints', 'test', '2024-12-31', '2024-01-01', 4),
            ('preprints', 'test', '2024-01-01', '9999-01-01', 4),
            ('preprints', 'test', None, '2024-01-01', 4),
            ('preprints', 'test', '20240101', '2024-12-31', 4),
            ('preprints', 'test', '2024-01-01', '2024-12-31', 21),
            ('preprints', 'test', '2024-01-01', '2024-12-31', True),
        ]:
            with self.subTest(provider=provider, query=query), self.assertRaises(ValueError):
                search_provider(provider, query, start, end, limit, client)
        self.assertEqual(client.urls, [])

    def test_preprint_identity_provenance_and_query(self):
        result, client = self.search('preprints', PREPRINT)
        item = result['items'][0]
        self.assertEqual(item['kind'], 'preprint')
        self.assertIsNone(item['pmid'])
        self.assertIn('no se presume', item['evidence_status'])
        self.assertNotIn('quartile_details', item)
        self.assertIn('No aplica', item['quartile'])
        self.assertNotIn('<i>', item['title'])
        expression = parse_qs(urlparse(client.urls[0]).query)['query'][0]
        self.assertIn('SRC:PPR', expression)
        self.assertIn('FIRST_PDATE:[2024-01-01 TO 2024-12-31]', expression)
        self.assertEqual(item['url'], 'https://europepmc.org/article/PPR/PPR999999999')

    def test_preprint_cannot_silently_become_pubmed_paper(self):
        bad = copy.deepcopy(PREPRINT)
        bad['resultList']['result'][0]['source'] = 'MED'
        with self.assertRaises(ValueError):
            self.search('preprints', bad)

    def test_crossref_preserves_precision_and_historical_issn_metric(self):
        result, client = self.search('crossref', CROSSREF)
        item = result['items'][0]
        self.assertEqual(item['published'], '2024-02')
        self.assertEqual(item['quartile'], 'Q2')
        self.assertEqual(item['quartile_details']['metric_year'], 2023)
        self.assertEqual(item['id'], '10.9999/synthetic-crossref')
        self.assertIsNone(item['pmid'])
        self.assertNotIn('<jats', item['summary'])
        self.assertIn('no comprobada', item['evidence_status'])
        query = parse_qs(urlparse(client.urls[0]).query)
        self.assertEqual(query['sort'], ['relevance'])
        self.assertIn('type:journal-article', query['filter'][0])
        self.assertIn('No equivale', result['query_semantics'])

    def test_crossref_missing_abstract_is_metadata_only(self):
        raw = copy.deepcopy(CROSSREF)
        raw['message']['items'][0].pop('abstract')
        result, _ = self.search('crossref', raw)
        self.assertTrue(result['items'][0]['metadata_only'])
        self.assertIsNone(result['items'][0]['summary'])

    def test_trials_use_updated_record_date_and_never_claim_efficacy(self):
        result, client = self.search('trials', TRIAL)
        item = result['items'][0]
        self.assertEqual(item['kind'], 'trial')
        self.assertEqual(item['published'], '2024-02-03')
        self.assertEqual(item['first_posted'], '2020-01-01')
        self.assertIn('actualización', item['date_basis'])
        self.assertIn('no demuestra eficacia', item['evidence_status'])
        self.assertEqual(item['trial_phase'], ['PHASE1'])
        self.assertFalse(item['has_results'])
        self.assertEqual(item['enrollment'], 20)
        self.assertIn('LastUpdatePostDate', parse_qs(urlparse(client.urls[0]).query)['query.term'][0])
        self.assertNotIn('quartile_details', item)

    def test_bad_external_fields_are_rejected(self):
        bad_preprint = copy.deepcopy(PREPRINT)
        bad_preprint['resultList']['result'][0]['title'] = {'bad': 'object'}
        bad_crossref = copy.deepcopy(CROSSREF)
        bad_crossref['message']['items'][0]['published']['date-parts'] = [[2024, 13]]
        bad_trial = copy.deepcopy(TRIAL)
        bad_trial['studies'][0]['hasResults'] = 'false'
        for provider, raw in [('preprints', bad_preprint), ('crossref', bad_crossref), ('trials', bad_trial)]:
            with self.subTest(provider=provider), self.assertRaises(ValueError):
                self.search(provider, raw)

    def test_empty_source_does_not_invent_records(self):
        for provider, raw in [('preprints', {'hitCount': 0, 'resultList': {'result': []}}),
                              ('crossref', {'message': {'total-results': 0, 'items': []}}),
                              ('trials', {'totalCount': 0, 'studies': []})]:
            result, _ = self.search(provider, raw)
            self.assertEqual(result['items'], [])
            self.assertEqual(result['total'], 0)

    def test_count_without_records_is_failure(self):
        with self.assertRaises(ValueError):
            self.search('trials', {'totalCount': 2, 'studies': []})

    def test_pubmed_retraction_notice_is_not_ordinary_evidence(self):
        raw = XML_FIXTURE.replace(b'<PublicationType>Review</PublicationType>',
                                  b'<PublicationType>Retracted Publication</PublicationType>')
        client = FakeClient({'esearchresult': {'idlist': ['999999999'], 'count': '1'}}, raw)
        result = search_provider('pubmed', 'PUBLIC TEST', '2024-01-01', '2024-12-31', client=client)
        self.assertIn('retraction', result['items'][0]['flags'])
        self.assertIn('retractada', result['items'][0]['evidence_status'])

    def test_pubmed_preprint_cannot_inherit_journal_quartile(self):
        raw = XML_FIXTURE.replace(b'<PublicationType>Review</PublicationType>',
                                  b'<PublicationType>Preprint</PublicationType>')
        raw = raw.replace(b'<Journal>', b'<Journal><ISSN>1111-1111</ISSN>')
        client = FakeClient({'esearchresult': {'idlist': ['999999999'], 'count': '1'}}, raw)
        result = search_provider('pubmed', 'PUBLIC TEST', '2024-01-01', '2024-12-31', client=client)
        item = result['items'][0]
        self.assertEqual(item['source'], 'pubmed')
        self.assertEqual(item['kind'], 'preprint')
        self.assertIn('no se presume revisión por pares', item['evidence_status'])
        self.assertEqual(item['quartile'], 'No aplica: preprint')
        self.assertNotIn('quartile_details', item)

    def test_preprint_retraction_warning_takes_precedence(self):
        raw = XML_FIXTURE.replace(b'<PublicationType>Review</PublicationType>',
                                  b'<PublicationType>Preprint</PublicationType><PublicationType>Retracted Publication</PublicationType>')
        client = FakeClient({'esearchresult': {'idlist': ['999999999'], 'count': '1'}}, raw)
        result = search_provider('pubmed', 'PUBLIC TEST', '2024-01-01', '2024-12-31', client=client)
        item = result['items'][0]
        self.assertEqual(item['kind'], 'preprint')
        self.assertIn('retractada', item['evidence_status'])
        self.assertIn('retraction', item['flags'])
        self.assertNotIn('quartile_details', item)

    def test_missing_trial_results_status_remains_unknown(self):
        raw = copy.deepcopy(TRIAL)
        raw['studies'][0].pop('hasResults')
        result, _ = self.search('trials', raw)
        self.assertIsNone(result['items'][0]['has_results'])

    def test_manual_links_are_safe_and_do_not_pretend_to_be_results(self):
        result = external_search_links('medical AND multimodal <test>')
        self.assertEqual(len(result['patent_links']), 3)
        self.assertEqual(len(result['social_links']), 1)
        for item in result['patent_links']:
            self.assertFalse(item['automatic'])
            self.assertFalse(item['prefilled'])
            self.assertIn('No se han recuperado resultados', item['note'])
            self.assertTrue(item['url'].startswith('https://'))
        social = result['social_links'][0]
        self.assertEqual(urlparse(social['url']).hostname, 'bsky.app')
        self.assertEqual(parse_qs(urlparse(social['url']).query)['q'], ['medical AND multimodal <test>'])
        self.assertIn('Señal social', social['note'])


if __name__ == '__main__':
    unittest.main()
