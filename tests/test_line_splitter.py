import unittest

from pagexml.parser import json_to_pagexml_line

from republic.parser.pagexml.long_line_splitter import SplitWord, LineSplitter

line_json = {"id": "NL-HaNA_1.10.94_456_0008-line-2625-2341-1806-79", "type": ["structure_doc", "physical_structure_doc", "line", "pagexml_doc"], "main_type": "line", "domain": "physical", "metadata": {"custom_attributes": [{"index": "7", "tag_name": "readingOrder"}], "reading_order": {"index": "7"}, "type": "line", "parent_type": "text_region", "parent_id": "NL-HaNA_1.10.94_456_0008-text_region-2581-2099-1853-1186", "text_region_id": "NL-HaNA_1.10.94_456_0008-text_region-2581-2099-1853-1186", "scan_id": "NL-HaNA_1.10.94_456_0008", "height": {"max": 58, "min": 28, "mean": 43, "median": 40}, "line_width": "full", "left_alignment": "indent", "right_alignment": "column", "column_id": "NL-HaNA_1.10.94_456_0008-column-2575-422-1859-2863", "page_id": "NL-HaNA_1.10.94_456_0008-page-15"}, "coords": [[2625, 2352], [2670, 2354], [2689, 2363], [2779, 2363], [2795, 2348], [3003, 2343], [3011, 2351], [3243, 2352], [3251, 2344], [3311, 2341], [3317, 2347], [3411, 2347], [3419, 2354], [3455, 2354], [3467, 2363], [3547, 2359], [3555, 2367], [3570, 2359], [3619, 2366], [3626, 2359], [3678, 2363], [3702, 2355], [3831, 2367], [3868, 2355], [3931, 2358], [3946, 2352], [3997, 2352], [4009, 2361], [4020, 2352], [4064, 2352], [4079, 2362], [4098, 2354], [4165, 2359], [4172, 2352], [4238, 2355], [4270, 2348], [4301, 2362], [4325, 2348], [4431, 2358], [4431, 2397], [4297, 2398], [4282, 2413], [4235, 2398], [4203, 2405], [4080, 2402], [4073, 2408], [4062, 2402], [3734, 2406], [3719, 2416], [3706, 2416], [3696, 2406], [3626, 2406], [3592, 2409], [3581, 2420], [3540, 2406], [3443, 2406], [3428, 2417], [3408, 2417], [3397, 2406], [3325, 2406], [3313, 2417], [3268, 2409], [2986, 2409], [2975, 2420], [2940, 2409], [2746, 2406], [2703, 2416], [2681, 2406], [2625, 2406]], "text": "Odijck, Becker, van Hecke, met twee extra- dertighsten der voorlede maendt, geaddresseert aen", "baseline": [[2644, 2397], [2694, 2396], [2894, 2401], [3144, 2402], [3494, 2397], [3544, 2398], [3694, 2398], [4294, 2389], [4394, 2389], [4413, 2388]]}


class TestLineSplitter(unittest.TestCase):

    def setUp(self) -> None:
        line = json_to_pagexml_line(line_json)
        self.test_line_group = [line]

    def test_split_word_candidates(self):
        line_splitter = LineSplitter(min_merged_width=1200, column_sep_width=20, default_line_num_chars=45,
                                     default_line_width=900, text_left_boundary=2560, text_right_boundary=4400)
        line_splitter.get_split_word_candidates(self.test_line_group, line_pos='centre')
