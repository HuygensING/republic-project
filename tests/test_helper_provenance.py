import unittest
import json

import republic.helper.provenance_helper as provenance_helper
from republic.config.republic_config import get_base_config
from republic.elastic.republic_elasticsearch import set_elasticsearch_config


class TestValidateProvenance(unittest.TestCase):

    def setUp(self) -> None:
        self.record = {
            'who': 'me', 'where': 'here', 'when': 'now', 'how': 'well', 'why': 'because',
            'source': ['source_1'], 'source_rel': ['primary'],
            'target': ['target_1'], 'target_rel': ['primary']
        }

    def test_validate_provenance_record_rejects_non_dict(self):
        record = 'provenance'
        self.assertRaises(TypeError, provenance_helper.validate_provenance_record, record)

    def test_validate_provenance_record_rejects_empty_dict(self):
        record = {}
        self.assertRaises(KeyError, provenance_helper.validate_provenance_record, record)

    def test_validate_provenance_record_rejects_non_string_why(self):
        self.record['why'] = None
        print(self.record)
        self.assertRaises(TypeError, provenance_helper.validate_provenance_record, self.record)

    def test_validate_provenance_record_rejects_unequal_urls_and_rels(self):
        self.record['source_rel'].append('primary')
        self.assertRaises(ValueError, provenance_helper.validate_provenance_record, self.record)


class TestGenerateESProvenance(unittest.TestCase):

    def setUp(self) -> None:
        self.inv_num = 3761
        self.es_config = get_base_config(self.inv_num)
        self.es_config = set_elasticsearch_config('external')
        self.source_es_url = 'https://test.es_instance.org/'
        self.ext_url = 'uri:external'

    def test_generate_provenance_urls_accepts_doc_ids_from_string(self):
        index = 'test_index'
        doc_ids = 'doc1'
        prov_urls = provenance_helper.generate_es_provenance_urls(doc_ids, index, self.source_es_url)
        for ui, url in enumerate(prov_urls):
            with self.subTest(ui):
                self.assertEqual(True, url.startswith(self.source_es_url))

    def test_generate_provenance_urls_uses_es_url_from_list(self):
        index = 'test_index'
        doc_ids = ['doc1', 'doc2']
        prov_urls = provenance_helper.generate_es_provenance_urls(doc_ids, index, self.source_es_url)
        self.assertEqual(True, all(url.startswith(self.source_es_url) for url in prov_urls))

    def test_generate_provenance_urls_includes_doc_ids(self):
        index = 'test_index'
        doc_ids = ['doc1', 'doc2']
        prov_urls = provenance_helper.generate_es_provenance_urls(doc_ids, index, self.source_es_url)
        for di, doc_id in enumerate(doc_ids):
            with self.subTest(di):
                self.assertEqual(True, any(url.endswith(doc_id) for url in prov_urls))

    def test_generate_provenance_urls_rels_generates_rels(self):
        index = 'test_index'
        doc_ids = ['doc1', 'doc2']
        rel_type = 'primary'
        urls, rels = provenance_helper.generate_es_provenance_urls_rels(doc_ids, index, self.source_es_url, rel_type)
        self.assertEqual(True, len(urls) == len(rels) and all(rel == rel_type for rel in rels))


class TestMakeProvenance(unittest.TestCase):

    def setUp(self) -> None:
        self.inv_num = 3761
        self.es_config = get_base_config(self.inv_num)
        self.es_config = set_elasticsearch_config('external')
        self.source_es_url = 'https://test.es_instance.org/'
        self.ext_url = 'uri:external'

    def test_can_make_provenance_record_for_sinle_source_single_target(self):
        source_index, target_index = 'sources', 'targets'
        source_id, target_id = 'source_1', 'target_1'
        why = 'deriving target from source'
        commit_url = 'https://github.com/test_user/test_repo/test_commit'
        source_urls = provenance_helper.generate_es_provenance_urls(source_id, source_index, self.source_es_url)
        target_urls = provenance_helper.generate_es_provenance_urls(target_id, target_index, self.source_es_url)
        source_rels = ['primary'] * len(source_urls)
        target_rels = ['primary'] * len(target_urls)
        record = provenance_helper.make_provenance_record(commit_url, why, source_urls, source_rels,
                                                          target_urls, target_rels)
        self.assertEqual(True, False)

    def test_can_make_provenance_for_index_to_index(self):
        source_index = 'sources'
        target_index = 'targets'
        source_id = 'source_1'
        target_id = 'target_1'
        why = 'deriving target from source'
        prov_data = provenance_helper.make_provenance_data(self.es_config, source_id, target_id,
                                                           source_index, target_index,
                                                           source_es_url=self.source_es_url,
                                                           source_external_urls=self.ext_url,
                                                           why=why)
        print(json.dumps(prov_data, indent=4))
        self.assertEqual(True, isinstance(prov_data, dict))
