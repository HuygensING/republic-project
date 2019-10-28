import json
import copy
from typing import Dict, List, Any, Union

from parse_hocr_files import make_hocr_page, filter_tiny_words_from_lines
import republic_elasticsearch as rep_es
import republic_index_page_parser as index_parser
import republic_base_page_parser as page_parser
import republic_resolution_page_parser as resolution_parser
from republic_phrase_model import resolution_phrases, spelling_variants
from fuzzy_context_searcher import FuzzyContextSearcher
config = {
    "char_match_threshold": 0.8,
    "ngram_threshold": 0.6,
    "levenshtein_threshold": 0.8,
    "ignorecase": False,
    "ngram_size": 2,
    "skip_size": 2,
}

fuzzy_searcher = FuzzyContextSearcher(config)
fuzzy_searcher.index_keywords(resolution_phrases)
fuzzy_searcher.index_spelling_variants(spelling_variants)


def get_page_columns_hocr(page_info, config):
    return {column_info["column_id"]: get_column_hocr(column_info, config) for column_info in page_info["columns"]}


def get_column_hocr(column_info, config):
    hocr_page = make_hocr_page(column_info["filepath"], column_info["column_id"], config=config)
    column_hocr = hocr_page.carea
    column_hocr["lines"] = hocr_page.lines
    if "remove_tiny_words" in config and config["remove_tiny_words"]:
        column_hocr["lines"] = filter_tiny_words_from_lines(hocr_page, config)
    return column_hocr


def determine_scan_type(scan_hocr: dict, config: dict) -> list:
    if "normal_scan_width" not in config:
        return ["unknown"]
    if scan_hocr["hocr_box"]["width"] > config["normal_scan_width"] * 1.1:
        return ["special", "extended"]
    elif scan_hocr["hocr_box"]["width"] < config["normal_scan_width"] * 0.9:
        return ["special", "small"]
    else:
        return ["normal", "double_page"]


def get_scan_hocr(scan_info, config):
    hocr_page = make_hocr_page(scan_info["filepath"], scan_info["scan_num"], config)
    scan_hocr: Dict[str, Union[Union[List[int], int], Any]] = hocr_page.carea
    scan_hocr["scan_num"] = scan_info["scan_num"]
    scan_hocr["scan_id"] = "year-{}-scan-{}".format(scan_info["inventory_year"], scan_info["scan_num"])
    scan_hocr["filepath"] = scan_info["filepath"]
    scan_hocr["inventory_num"] = scan_info["inventory_num"]
    scan_hocr["inventory_year"] = scan_info["inventory_year"]
    scan_hocr["inventory_period"] = scan_info["inventory_period"]
    scan_hocr["hocr_box"] = hocr_page.box
    scan_hocr["scan_type"] = determine_scan_type(scan_hocr, config)
    scan_hocr["lines"] = hocr_page.lines
    if "remove_tiny_words" in config and config["remove_tiny_words"]:
        scan_hocr["lines"] = filter_tiny_words_from_lines(hocr_page, config)
    return scan_hocr


def get_page_type(page_hocr: dict, debug: bool = False) -> str:
    resolution_score = 0
    index_score = 0
    if page_hocr["num_columns"] == 0:
        return "empty_page"
    for column_hocr in page_hocr["columns"]:
        #if not "column_hocr" in column_hocr:
        #    return "bad_page"
        #column_hocr = column_hocr["column_hocr"]
        #if not page_parser.proper_column_cut(column_hocr):
        #    page_type = "bad_page"
        #    return page_type
        column_header_line = page_parser.get_column_header_line(column_hocr)
        if not column_header_line:
        #    print("\t\tNO HEADER LINE for column id", column_hocr["column_id"])
            continue
        resolution_score += resolution_parser.score_resolution_header(column_header_line, column_hocr, debug=debug)
        index_score += index_parser.score_index_header(column_header_line, column_hocr, debug=debug)
    if index_parser.count_page_ref_lines(page_hocr) >= 10:
        index_score += int(index_parser.count_page_ref_lines(page_hocr) / 10)
        if debug:
            print("\tIndex test - many page references:", index_parser.count_page_ref_lines(page_hocr))
    if index_parser.count_repeat_symbols_page(page_hocr) == 0:
        resolution_score += 1
        if debug:
            print("\tResolution test - no repeat symbols:")
    else:
        index_score += index_parser.count_repeat_symbols_page(page_hocr)
        if debug and index_parser.count_repeat_symbols_page(page_hocr) > 3:
            print("\tIndex test - many repeat symbols:", index_parser.count_repeat_symbols_page(page_hocr))
    if page_parser.calculate_left_jumps(page_hocr) < 0.3:
        resolution_score += (1 - page_parser.calculate_left_jumps(page_hocr)) * 10
        if (debug):
            print("\tfew left jumps")
    elif page_parser.calculate_left_jumps(page_hocr) > 0.5:
        if (debug):
            print("\tmany left jumps")
        index_score += page_parser.calculate_left_jumps(page_hocr) * 10
    text = " ".join([line["line_text"] for column in page_hocr["columns"] for line in column["lines"]])
    phrase_matches = fuzzy_searcher.find_candidates(text)
    if phrase_matches:
        resolution_score += len(phrase_matches)
        if debug:
            print("\tresolution phrase matches:", len(phrase_matches))
    if debug:
        print("res_score:", resolution_score, "ind_score:", index_score)
        print(" ".join(page_parser.get_page_header_words(page_hocr)))
    if resolution_score >= 5 and resolution_score > index_score:
        return "resolution_page"
    elif index_score >= 4 and index_score > resolution_score:
        return "index_page"
    else:
        return "unknown_page_type"


def do_page_indexing(pages_info, config, delete_index=False):
    numbering = 0
    if delete_index:
        rep_es.delete_es_index(config["page_index"])
    for page_id in pages_info:
        numbering += 1
        if pages_info[page_id]["scan_num"] <= 0:
            continue
        if pages_info[page_id]["scan_num"] >= 700:
            continue
        page_info = copy.deepcopy(pages_info[page_id])
        for column_info in page_info["columns"]:
            try:
                column_info["column_hocr"] = get_column_hocr(column_info, config)
            except TypeError:
                print("Error parsing file", column_info["filepath"])
        try:
            page_type = get_page_type(page_info, config, debug=False)
        except TypeError:
            print(json.dumps(page_info, indent=2))
            raise
        page_info["page_type"] = page_type
        page_info["is_parseable"] = True if page_type != "bad_page" else False
        if page_parser.is_title_page(page_info):
            numbering = 1 # reset numbering
            page_info["is_title_page"] = True
        else:
            page_info["is_title_page"] = False
        page_info["type_page_num"] = numbering
        page_info["type_page_num_checked"] = False
        page_doc = rep_es.create_es_page_doc(page_info)
        rep_es.es.index(index=config["page_index"], doc_type=config["page_doc_type"], id=page_id, body=page_doc)
        print(page_id, page_type, numbering)



