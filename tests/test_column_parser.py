import json
import unittest

from pagexml.parser import json_to_pagexml_page, read_pagexml_file

import republic.parser.pagexml.republic_column_parser as col_parser


class TestColumnParser(unittest.TestCase):

    def setUp(self) -> None:
        self.page_files = {
            'page1': './tests/test_data/NL-HaNA_1.01.02_4542_0002-page-2-date-2023-12-19.json'
        }

    def test_page_1(self):
        page_json = json.loads(read_pagexml_file(self.page_files['page1']))
        page = json_to_pagexml_page(page_json)
        for col in page.columns:
            print('old_col:', col.id)
            for tr in col.text_regions:
                print('\told_tr:', tr.id)
        num_old_col_trs = [3, 1]
        num_new_col_trs = [4, 5]
        for ci, old_col in enumerate(page.columns):
            new_col = col_parser.split_column_text_regions(old_col, debug=1)
            with self.subTest(ci):
                self.assertEqual(num_old_col_trs[ci], len(old_col.text_regions))
                self.assertEqual(num_new_col_trs[ci], len(new_col.text_regions))
