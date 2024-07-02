from unittest import TestCase

from republic.model.republic_stats_doc import StatsDoc
from republic.model.republic_stats_doc import merge_stats_docs_list


class TestStatsDocInit(TestCase):

    def setUp(self) -> None:
        self.page_doc = {
            'doc_id': 'page_1',
            'doc_type': 'PageXMLPage',
            'inv_num': 1,
            'words': 0,
            'lines': 0
        }
        self.session_doc = {
            'doc_id': 'session_1',
            'doc_type': 'Session',
            'inv_num': 1,
            'words': 0,
            'lines': 0,
            'page_stats_docs': [self.page_doc]
        }
        self.page_stats_doc = StatsDoc(self.page_doc['doc_id'], self.page_doc['doc_type'], self.page_doc['inv_num'],
                                       self.page_doc['words'], self.page_doc['lines'])
        self.session_stats_doc = StatsDoc(self.session_doc['doc_id'], self.session_doc['doc_type'],
                                          self.session_doc['inv_num'], self.session_doc['words'],
                                          self.session_doc['lines'], page_stats_docs=[self.page_stats_doc])

    def test_stats_doc_init_basic(self):
        stats_doc = StatsDoc(self.page_doc['doc_id'], self.page_doc['doc_type'], self.page_doc['inv_num'],
                             self.page_doc['words'], self.page_doc['lines'])
        for ai, attr in enumerate(self.page_doc):
            with self.subTest(ai):
                self.assertEqual(True, hasattr(stats_doc, attr))

    def test_stats_doc_generates_json(self):
        stats_doc = StatsDoc(self.page_doc['doc_id'], self.page_doc['doc_type'], self.page_doc['inv_num'],
                             self.page_doc['words'], self.page_doc['lines'])
        self.assertEqual(self.page_doc, stats_doc.to_json())

    def test_session_stats_doc_includes_page_stats_docs(self):
        session_stats_doc = StatsDoc(self.session_doc['doc_id'], self.session_doc['doc_type'],
                                     self.session_doc['inv_num'], self.session_doc['words'],
                                     self.session_doc['lines'], page_stats_docs=[self.page_stats_doc])
        self.assertEqual(True, self.page_stats_doc in session_stats_doc.page_stats_docs)

    def test_stats_doc_generates_json_including_page_stats_docs(self):
        session_stats_doc = StatsDoc(self.session_doc['doc_id'], self.session_doc['doc_type'],
                                     self.session_doc['inv_num'], self.session_doc['words'],
                                     self.session_doc['lines'], page_stats_docs=[self.page_stats_doc])
        self.assertEqual(True, 'page_stats_docs' in session_stats_doc.to_json())
        self.assertEqual(1, len(session_stats_doc.to_json()['page_stats_docs']))
        self.assertEqual(self.page_doc, session_stats_doc.to_json()['page_stats_docs'][0])

    def test_stats_doc_instantiates_from_json(self):
        stats_doc = StatsDoc.from_json(self.page_doc)
        self.assertEqual(self.page_doc, stats_doc.to_json())

    def test_stats_doc_instantiates_page_stats_docs_from_json(self):
        stats_doc = StatsDoc.from_json(self.session_doc)
        print('\n-----------\nsession_doc\n', self.session_doc)
        print('\n-----------\nstats_doc.to_json()\n', stats_doc.to_json())
        self.assertEqual(self.session_doc, stats_doc.to_json())

    def test_merge_docs_not_accept_list_with_non_stats_doc_types(self):
        stats_docs = [self.page_stats_doc, self.page_doc]
        self.assertRaises(TypeError, merge_stats_docs_list, stats_docs)

    def test_merge_docs_accepts_list_with_different_doc_types(self):
        stats_docs = [self.page_stats_doc, self.session_stats_doc]
        error = None
        try:
            merge_stats_docs_list(stats_docs)
        except BaseException as err:
            error = err
        self.assertEqual(None, error)

    def test_merge_docs_does_nothing_if_no_repeated_doc_id(self):
        stats_docs = [self.page_stats_doc, self.session_stats_doc]
        merged_docs = merge_stats_docs_list(stats_docs)
        self.assertEqual(len(stats_docs), len(merged_docs))

    def test_merge_docs_returns_copies_of_singletons(self):
        stats_docs = [self.page_stats_doc, self.session_stats_doc]
        merged_docs = merge_stats_docs_list(stats_docs)
        for si, sd in enumerate(stats_docs):
            with self.subTest(si):
                self.assertNotIn(sd, merged_docs)

    def test_merge_docs_reduces_if_repeated_doc_id(self):
        stats_docs = [self.page_stats_doc, self.page_stats_doc]
        merged_docs = merge_stats_docs_list(stats_docs)
        self.assertEqual(1, len(merged_docs))

    def test_merge_docs_adds_words_of_repeated_doc_id(self):
        stats_docs = [self.page_stats_doc, self.page_stats_doc]
        merged_docs = merge_stats_docs_list(stats_docs)
        total_words = sum([sd.words for sd in stats_docs])
        self.assertEqual(total_words, merged_docs[0].words)

    def test_merge_docs_adds_lines_of_repeated_doc_id(self):
        stats_docs = [self.page_stats_doc, self.page_stats_doc]
        merged_docs = merge_stats_docs_list(stats_docs)
        total_lines = sum([sd.lines for sd in stats_docs])
        self.assertEqual(total_lines, merged_docs[0].lines)

    def test_merge_docs_adds_lines_of_repeated_page_stats_doc_id(self):
        stats_docs = [self.session_stats_doc, self.session_stats_doc]
        merged_docs = merge_stats_docs_list(stats_docs)
        total_lines = sum([psd.lines for sd in stats_docs for psd in sd.page_stats_docs])
        self.assertEqual(total_lines, merged_docs[0].page_stats_docs[0].lines)


