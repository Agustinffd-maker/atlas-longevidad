"""Configuraciones y términos sintéticos: no contienen un perfil de investigación real."""
import json
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from research_profile import (LONGEVITY_QUERY, build_research_queries, delete_profile,
                              get_concept_suggestions, load_profile, save_profile,
                              validate_profile)


class ResearchProfileTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.path = Path(self.folder.name) / 'profile.json'
        self.values = dict(enabled=True, title='SYNTHETIC TEST', concepts=['IA multimodal', 'célula virtual'],
                           synonyms={'IA multimodal': ['multimodal artificial intelligence']})

    def tearDown(self):
        self.folder.cleanup()

    def test_absent_profile_is_disabled_and_not_created(self):
        profile = load_profile(self.path)
        self.assertFalse(profile['enabled'])
        self.assertEqual(profile['concepts'], [])
        self.assertFalse(self.path.exists())
        self.assertEqual(build_research_queries(profile, 'thesis'), [])

    def test_save_round_trip_is_local_private_and_does_not_enable_by_default(self):
        with patch('socket.create_connection', side_effect=AssertionError('No network permitted')):
            profile = save_profile(self.path, dict(concepts=['IA multimodal']))
            self.assertEqual(load_profile(self.path), profile)
        self.assertFalse(profile['enabled'])
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode) & 0o077, 0)
        self.assertTrue(profile['updated_at'])
        self.assertNotIn('storage_warning', profile)

    def test_failed_atomic_replace_preserves_previous_profile_and_cleans_temporary(self):
        save_profile(self.path, self.values)
        previous = self.path.read_bytes()
        with patch('research_profile.os.replace', side_effect=OSError('SYNTHETIC WRITE FAILURE')):
            with self.assertRaises(OSError):
                save_profile(self.path, dict(self.values, title='CHANGED SYNTHETIC TEST'))
        self.assertEqual(self.path.read_bytes(), previous)
        self.assertEqual(list(self.path.parent.glob('*.tmp')), [])

    def test_corrupt_profile_warns_without_overwriting_or_enabling(self):
        self.path.write_text('{invalid fixture')
        result = load_profile(self.path)
        self.assertFalse(result['enabled'])
        self.assertTrue(result['storage_warning'])
        self.assertEqual(self.path.read_text(), '{invalid fixture')

    def test_delete_preserves_other_local_files(self):
        other = self.path.parent / 'other.json'
        other.write_text('{}')
        save_profile(self.path, self.values)
        self.assertFalse(delete_profile(self.path)['enabled'])
        self.assertFalse(self.path.exists())
        self.assertTrue(other.exists())
        self.assertFalse(delete_profile(self.path)['enabled'])

    def test_invalid_profile_contract_is_rejected(self):
        bad = [None, [], {'enabled': 1}, {'enabled': True}, {'concepts': 'IA multimodal'},
               {'concepts': ['x']}, {'concepts': ['x' * 81]}, {'concepts': ['test'] * 7},
               {'concepts': ['célula virtual', 'CELULA VIRTUAL']}, {'concepts': [None]},
               {'title': 'x' * 101}, {'schema_version': True}, {'schema_version': 2},
               {'updated_at': 'yesterday'}, {'updated_at': '2026-11-10'},
               {'concepts': ['IA multimodal'], 'synonyms': {'missing': ['test']}},
               {'concepts': ['IA multimodal'], 'synonyms': {'IA multimodal': 'test'}},
               {'concepts': ['IA multimodal'], 'synonyms': {'IA multimodal': ['test'] * 6}}]
        for values in bad:
            with self.subTest(values=values), self.assertRaises(ValueError):
                validate_profile(values)

    def test_query_syntax_is_quoted_or_rejected_and_unknown_fields_are_discarded(self):
        for concept in ('IA" OR all', 'test\\escape', 'line\nfeed'):
            with self.subTest(concept=concept), self.assertRaises(ValueError):
                validate_profile({'concepts': [concept]})
        profile = validate_profile({'enabled': True, 'concepts': ['foo OR bar'],
                                    'unrequested_field': 'SYNTHETIC DATA NOT STORED'})
        self.assertNotIn('unrequested_field', profile)
        query = build_research_queries(profile, 'thesis')[0]['query']
        self.assertEqual(query, '("foo OR bar")')

    def test_queries_are_separate_per_concept_with_optional_longevity_bridge(self):
        direct = build_research_queries(self.values, 'thesis')
        bridges = build_research_queries(self.values, 'combined')
        self.assertEqual(len(direct), 2)
        self.assertEqual(len(bridges), 2)
        self.assertEqual(direct[0]['concepts'], ['IA multimodal'])
        self.assertNotIn('célula virtual', direct[0]['query'])
        self.assertIn('"multimodal artificial intelligence"', direct[0]['query'])
        self.assertNotIn(LONGEVITY_QUERY, direct[0]['query'])
        self.assertTrue(all(item['query'].startswith(LONGEVITY_QUERY + ' AND ') for item in bridges))
        self.assertFalse(self.path.exists())

    def test_long_queries_keep_user_variants_within_radar_limit(self):
        concepts = ['SYNTHETIC CONCEPT ' + str(index) for index in range(6)]
        synonyms = {term: ['SYNTHETIC VARIANT ' + str(index) + ' x' * 25 for index in range(5)] for term in concepts}
        queries = build_research_queries(dict(enabled=True, concepts=concepts, synonyms=synonyms), 'combined')
        self.assertEqual(len(queries), 6)
        self.assertTrue(all(len(item['query']) <= 1000 for item in queries))
        for item in queries:
            for variant in synonyms[item['concepts'][0]]:
                self.assertIn('"' + variant + '"', item['query'])

    def test_longevity_queries_work_without_research_configuration(self):
        queries = build_research_queries(None, 'longevity')
        self.assertEqual(len(queries), 6)
        self.assertEqual(queries[0]['query'], LONGEVITY_QUERY)
        with self.assertRaises(ValueError):
            build_research_queries(self.values, 'unknown')

    def test_suggestions_are_explained_sourced_and_do_not_autoadd_selected_concepts(self):
        profile = save_profile(self.path, self.values)
        previous = self.path.read_bytes()
        suggestions = get_concept_suggestions(profile['concepts'])
        self.assertTrue(suggestions)
        self.assertLessEqual(len(suggestions), 12)
        self.assertNotIn('multimodal artificial intelligence', [item['term'] for item in suggestions])
        self.assertEqual(self.path.read_bytes(), previous)
        for item in suggestions:
            self.assertTrue(item['reason'])
            self.assertTrue(item['source_url'].startswith('https://'))
            self.assertIn('Propuesta editorial', item['relation_note'])

    def test_unrecognized_project_gets_method_suggestions_without_fabricating_a_link(self):
        suggestions = get_concept_suggestions(['SYNTHETIC NEW TOPIC'])
        self.assertEqual({item['relation_type'] for item in suggestions}, {'method'})
        self.assertTrue(all('no presupone relación biológica' in item['reason'] for item in suggestions))
        self.assertEqual(get_concept_suggestions([]), suggestions)
