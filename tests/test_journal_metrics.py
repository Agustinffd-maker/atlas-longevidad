"""Comportamiento del cruce histórico: no se adivina la revista ni el cuartil."""
import copy
import unittest
from unittest.mock import patch

from journal_metrics import enrich_article
from sources import parse_pubmed, europe_search, validate_params
from test_app import FakeClient, XML_FIXTURE, METRICS_FIXTURE


class JournalMetricsTests(unittest.TestCase):
    def setUp(self):
        self.registry_patch = patch('journal_metrics.registry', return_value=METRICS_FIXTURE)
        self.registry_patch.start()
        self.addCleanup(self.registry_patch.stop)

    def test_verified_issn_keeps_historical_provenance_without_mutating_input(self):
        article = {'issns': ['1111-1111'], 'quartile': 'cuartil no verificado'}
        original = copy.deepcopy(article)
        result = enrich_article(article)
        self.assertEqual(article, original)
        self.assertEqual(result['quartile'], 'Q2')
        details = result['quartile_details']
        self.assertEqual(details['metric_year'], 2023)
        self.assertEqual(details['metric'], 'JIF Quartile')
        self.assertIn('SYNTHETIC CATEGORY', details['category'])
        self.assertTrue(details['source_url'].endswith('#page=12'))

    def test_name_missing_or_bad_issn_cannot_confirm_a_quartile(self):
        for issns in ([], ['0000-0000'], None, '1111-1111', [None]):
            result = enrich_article({'journal': 'SYNTHETIC JOURNAL A', 'issns': issns,
                                     'quartile': 'Q1', 'quartile_details': {'old': True}})
            self.assertEqual(result['quartile'], 'cuartil no verificado')
            self.assertNotIn('quartile_details', result)

    def test_conflicting_journals_cannot_confirm_a_quartile(self):
        result = enrich_article({'issns': ['1111-1111', '2222-2222']})
        self.assertEqual(result['quartile'], 'cuartil no verificado')

    def test_pubmed_extracts_print_and_linking_issn(self):
        raw = XML_FIXTURE.replace(b'<Journal>', b'<Journal><ISSN>1111-1111</ISSN>')
        raw = raw.replace(b'</MedlineCitation>',
                          b'<MedlineJournalInfo><ISSNLinking>1111-1111</ISSNLinking></MedlineJournalInfo></MedlineCitation>')
        result = parse_pubmed(raw)[0]
        self.assertEqual(result['issns'], ['1111-1111'])
        self.assertEqual(result['quartile'], 'Q2')

    def test_europe_pmc_extracts_issn_and_ignores_invalid_values(self):
        client = FakeClient({'hitCount': 1, 'resultList': {'result': [{
            'id': '999999999', 'source': 'MED', 'title': 'SYNTHETIC TEST',
            'journalInfo': {'journal': {'title': 'SYNTHETIC', 'issn': 'bad', 'essn': '1111-1111'}}
        }]}})
        articles, _ = europe_search(validate_params({'q': 'PUBLIC TEST', 'provider': 'europepmc'}), client)
        self.assertEqual(articles[0]['issns'], ['1111-1111'])
        self.assertEqual(articles[0]['quartile'], 'Q2')
