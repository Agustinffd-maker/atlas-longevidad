"""Fixtures sintéticas exclusivamente para probar comportamiento, no evidencia real."""
import copy
import json
import re
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from cache import EvidenceCache, now_iso
from sources import EvidenceService, parse_pubmed, pubmed_search, europe_search, plain_markup, validate_params

ROOT = Path(__file__).resolve().parents[1]
# PMID deliberadamente sintético: jamás se sirve como contenido de la aplicación.
XML_FIXTURE = b'''<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>999999999</PMID><Article><ArticleTitle>TEST SYNTHETIC: models &amp; data</ArticleTitle><Journal><Title>Test journal</Title><JournalIssue><PubDate><Year>2024</Year><Month>Feb</Month></PubDate></JournalIssue></Journal><Abstract><AbstractText Label="RESULTS">Synthetic result, not scientific evidence.</AbstractText></Abstract><PublicationTypeList><PublicationType>Review</PublicationType></PublicationTypeList></Article><MeshHeadingList><MeshHeading><DescriptorName>Humans</DescriptorName></MeshHeading></MeshHeadingList></MedlineCitation><PubmedData><ArticleIdList><ArticleId IdType="doi">10.1234/synthetic-test</ArticleId></ArticleIdList></PubmedData></PubmedArticle></PubmedArticleSet>'''


METRICS_FIXTURE = dict(metric='JIF Quartile', metric_year=2023,
    source_url='https://example.org/synthetic-metrics.pdf', journals=[
        dict(journal='SYNTHETIC JOURNAL A', issns=['1111-1111'], category='SYNTHETIC CATEGORY', quartile='Q2', pdf_page=12),
        dict(journal='SYNTHETIC JOURNAL B', issns=['2222-2222'], category='SYNTHETIC CATEGORY', quartile='Q1', pdf_page=13),
    ])


class FakeClient:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.urls = []

    def fetch(self, url):
        self.urls.append(url)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response if isinstance(response, bytes) else json.dumps(response).encode()


class ParameterTests(unittest.TestCase):
    def test_query_and_date_boundaries(self):
        for params in ({}, {"q":"x"}, {"q":"a"*251}, {"q":"valid\nquery"}, {"q":"test", "start":"2025-01-01", "end":"2024-01-01"}, {"q":"test", "end":"9999-01-01"}, {"q":"test", "start":"yesterday"}, {"q":"test", "kind":"fake"}, {"q":"test", "provider":"http://other.example"}, {"q":42}):
            with self.subTest(params=params), self.assertRaises(ValueError):
                validate_params(params)

    def test_normalized_contract(self):
        params = validate_params({"q":"  multimodal AI  "})
        self.assertEqual(params["q"], "multimodal AI")
        self.assertEqual(params["provider"], "pubmed")


class AdapterTests(unittest.TestCase):
    def test_external_markup_becomes_text_without_executing(self):
        self.assertEqual(plain_markup('Study of &lt;i&gt;models&lt;/i&gt; &amp; data'), 'Study of models & data')
        with self.assertRaises(ValueError):
            plain_markup({"not":"text"})

    def test_pubmed_metadata_provenance(self):
        article = parse_pubmed(XML_FIXTURE)[0]
        self.assertEqual(article["title"], "TEST SYNTHETIC: models & data")
        self.assertEqual(article["published"], "2024-02")
        self.assertEqual(article["date_precision"], "mes")
        self.assertEqual(article["model"], "Humanos (MeSH)")
        self.assertEqual(article["quartile"], "cuartil no verificado")
        self.assertEqual(article["doi"], "10.1234/synthetic-test")
        self.assertTrue(article["fetched_at"])

    def test_no_abstract_does_not_invent_summary(self):
        raw = XML_FIXTURE.replace(b'<Abstract><AbstractText Label="RESULTS">Synthetic result, not scientific evidence.</AbstractText></Abstract>',b'')
        article = parse_pubmed(raw)[0]
        self.assertIsNone(article["abstract"])
        self.assertEqual(article["access"], "Solo metadatos")

    def test_bad_xml_and_missing_id(self):
        for raw in (b'<wrong/>', XML_FIXTURE.replace(b'<PMID>999999999</PMID>', b'')):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                parse_pubmed(raw)

    def test_pubmed_empty_needs_no_fetch(self):
        client = FakeClient({"esearchresult":{"idlist":[],"count":"0"}})
        articles, count = pubmed_search(validate_params({"q":"empty test"}), client)
        self.assertEqual((articles,count),([],0))
        self.assertEqual(len(client.urls),1)

    def test_filters_reach_pubmed(self):
        client = FakeClient({"esearchresult":{"idlist":["999999999"],"count":"1"}}, XML_FIXTURE)
        params = validate_params({"q":"medical AI", "kind":"review", "model":"humans", "start":"2020-01-01", "end":"2024-12-31"})
        articles,count = pubmed_search(params,client)
        query = parse_qs(urlparse(client.urls[0]).query)
        self.assertIn('Humans[mh]',query["term"][0])
        self.assertIn('Review[pt]',query["term"][0])
        self.assertEqual(query["mindate"],["2020-01-01"])
        self.assertEqual((len(articles),count),(1,1))

    def test_invalid_ids_are_not_forwarded(self):
        client = FakeClient({"esearchresult":{"idlist":["bad&id=1"],"count":"1"}})
        with self.assertRaises(ValueError):
            pubmed_search(validate_params({"q":"test"}),client)
        self.assertEqual(len(client.urls),1)

    def test_europe_query_and_no_abstract(self):
        client = FakeClient({"hitCount":1,"resultList":{"result":[{"id":"999999999","source":"MED","title":"SYNTHETIC TEST","firstPublicationDate":"2024-01-01","pubTypeList":{"pubType":["review"]}}]}})
        params = validate_params({"q":"medical AI", "provider":"europepmc", "kind":"review", "model":"cells"})
        articles, count = europe_search(params,client)
        query = parse_qs(urlparse(client.urls[0]).query)["query"][0]
        self.assertIn('SRC:MED',query)
        self.assertIn('PUB_TYPE:review',query)
        self.assertIn('FIRST_PDATE:',query)
        self.assertIn('"in vitro"',query)
        self.assertEqual(count,1)
        self.assertIsNone(articles[0]["abstract"])
        self.assertIn('no determinado',articles[0]["model"])

    def test_europe_rejects_malformed_response(self):
        bad = [{}, {"hitCount":2,"resultList":{"result":[]}}, {"hitCount":1,"resultList":{"result":[None]}}, {"hitCount":1,"resultList":{"result":[{"id":"999999999","title":"SYNTHETIC","pubTypeList":{"pubType":"Review"}}]}}]
        for result in bad:
            with self.subTest(result=result), self.assertRaises(ValueError):
                europe_search(validate_params({"q":"test"}),FakeClient(result))


class CacheTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.path = Path(self.folder.name)/'evidence.json'
        self.cache = EvidenceCache(self.path)
        self.params = validate_params({"q":"SYNTHETIC test"})
        self.entry = dict(articles=parse_pubmed(XML_FIXTURE), total=1, query=self.params["q"], provider="pubmed", fetched_at=now_iso(), last_attempt_at=now_iso(), stale=False,error=None,cached=False)

    def tearDown(self):
        self.folder.cleanup()

    def test_cache_persists_and_keeps_queries_distinct(self):
        self.cache.put(self.params,self.entry)
        loaded = EvidenceCache(self.path)
        self.assertEqual(loaded.get(self.params)["articles"],self.entry["articles"])
        self.assertIsNone(loaded.get(dict(self.params, q="different query")))

    def test_expiration_and_future_dates(self):
        self.assertTrue(self.cache.fresh(self.entry))
        self.assertFalse(self.cache.fresh(dict(self.entry,fetched_at=(datetime.now(timezone.utc)-timedelta(days=2)).isoformat())))
        self.assertFalse(self.cache.fresh(dict(self.entry,fetched_at=(datetime.now(timezone.utc)+timedelta(days=2)).isoformat())))
        self.assertFalse(self.cache.fresh({}))

    def test_corrupt_cache_is_not_evidence(self):
        self.path.write_text('{bad json')
        self.assertIsNone(EvidenceCache(self.path).get(self.params))
        self.path.write_text('{"bad": []}')
        self.assertEqual(EvidenceCache(self.path).parameters(),[])

    def test_fresh_cache_avoids_network(self):
        self.cache.put(self.params,self.entry)
        result = EvidenceService(self.cache,FakeClient()).search(self.params)
        self.assertTrue(result["cached"])
        self.assertEqual(result["fetched_at"],self.entry["fetched_at"])

    def test_offline_preserves_old_results_and_date(self):
        self.entry["fetched_at"]=(datetime.now(timezone.utc)-timedelta(days=2)).isoformat()
        self.cache.put(self.params,self.entry)
        client=FakeClient(OSError('SIMULATED OFFLINE'))
        result = EvidenceService(self.cache,client).search(self.params)
        self.assertTrue(result["stale"])
        self.assertTrue(result["error"])
        self.assertEqual(result["articles"],self.entry["articles"])
        self.assertEqual(result["fetched_at"],self.entry["fetched_at"])
        self.assertEqual(self.cache.get(self.params)["fetched_at"],self.entry["fetched_at"])

    def test_offline_without_cache_invents_nothing(self):
        result = EvidenceService(self.cache,FakeClient(OSError())).search(self.params)
        self.assertEqual(result["articles"],[])
        self.assertIsNone(result["total"])
        self.assertIsNone(result["fetched_at"])
        self.assertTrue(result["stale"])

    def test_malformed_response_preserves_cache(self):
        self.cache.put(self.params,self.entry)
        result=EvidenceService(self.cache,FakeClient({"wrong":"shape"})).search(self.params,force=True)
        self.assertTrue(result["stale"])
        self.assertEqual(result["articles"],self.entry["articles"])

    def test_manual_refresh_and_cooldown(self):
        self.cache.put(self.params,self.entry)
        client=FakeClient({"esearchresult":{"idlist":[],"count":"0"}})
        service=EvidenceService(self.cache,client)
        result=service.search(self.params,force=True)
        self.assertEqual(result["articles"],[])
        self.assertEqual(result["total"],0)
        second=service.search(self.params,force=True)
        self.assertEqual(len(client.urls),1)
        self.assertTrue(second["cached"])

    def test_scheduler_waits_and_stops(self):
        import server
        stopped=unittest.mock.Mock()
        stopped.wait.side_effect=[False,True]
        stopped.is_set.return_value=False
        self.cache.put(self.params,self.entry)
        service=unittest.mock.Mock(cache=self.cache)
        server.periodic_refresh(service,stopped)
        service.search.assert_called_once_with(self.params)
        stopped.wait.assert_called_with(21600)


class ContentTests(unittest.TestCase):
    def setUp(self):
        self.catalog=json.loads((ROOT/'data/catalog.json').read_text())
        self.references=json.loads((ROOT/'data/reference_seed.json').read_text())

    def test_reference_integrity_and_traceability(self):
        ids={topic['id'] for topic in self.catalog['topics']}
        self.assertEqual(len(ids),len(self.catalog['topics']))
        for topic in self.catalog['topics']:
            for field in ('why','findings','limits','thesis'):
                self.assertTrue(topic[field]['text'])
                self.assertTrue(topic[field]['refs'])
                self.assertTrue(set(topic[field]['refs']) <= set(self.references))
            self.assertTrue(set(topic['refs']) <= set(self.references))
            self.assertTrue(topic['sample'] and topic['method'] and topic['units'])
        for connection in self.catalog['connections']:
            self.assertIn(connection['from'],ids)
            self.assertIn(connection['to'],ids)
            self.assertTrue(set(connection['refs']) <= set(self.references))
        for entry in self.catalog['glossary']:
            self.assertTrue(set(entry['refs']) <= set(self.references))
        terms={entry['term'] for entry in self.catalog['glossary']}
        for topic in self.catalog['topics']:
            self.assertTrue(set(topic['terms']) <= terms)
        for pmid, reference in self.references.items():
            self.assertEqual(pmid,reference['pmid'])
            self.assertEqual(reference['url'],'https://pubmed.ncbi.nlm.nih.gov/'+pmid+'/')
            self.assertTrue(reference['fetched_at'])
            if reference.get('quartile_details'):
                self.assertEqual(reference['quartile_details']['metric_year'], 2023)
                self.assertTrue(reference['quartile_details']['source_url'].startswith('https://'))
            else:
                self.assertEqual(reference['quartile'],'cuartil no verificado')

    def test_local_skills_have_discoverable_frontmatter(self):
        skills=list((ROOT/'.agents/skills').glob('*/SKILL.md'))
        self.assertEqual(len(skills),5)
        for path in skills:
            match=re.match(r'^---\nname: ([a-z0-9-]{1,64})\ndescription: ([^\n]+)\n---\n(.+)',path.read_text(),re.S)
            self.assertIsNotNone(match,str(path))
            self.assertEqual(match.group(1),path.parent.name)
            self.assertNotIn('TODO',match.group(3))
            self.assertLess(len(match.group(2)),1024)


if __name__=='__main__':
    unittest.main()
