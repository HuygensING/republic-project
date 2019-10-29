import copy
from typing import Dict, List, Any, Union

from republic.model.republic_hocr_model import make_hocr_page, filter_tiny_words_from_lines
import republic.parser.republic_base_page_parser as base_parser
import republic.parser.republic_index_page_parser as index_parser
import republic.parser.republic_resolution_page_parser as resolution_parser
import republic.parser.republic_column_parser as column_parser
from republic.model.republic_phrase_model import resolution_phrases, spelling_variants
from republic.fuzzy.fuzzy_context_searcher import FuzzyContextSearcher

fuzzy_search_config = {
    "char_match_threshold": 0.8,
    "ngram_threshold": 0.6,
    "levenshtein_threshold": 0.8,
    "ignorecase": False,
    "ngram_size": 2,
    "skip_size": 2,
}

fuzzy_searcher = FuzzyContextSearcher(fuzzy_search_config)
fuzzy_searcher.index_keywords(resolution_phrases)
fuzzy_searcher.index_spelling_variants(spelling_variants)


def get_page_columns_hocr(page_info: object, config: dict) -> object:
    return {column_info["column_id"]: get_column_hocr(column_info, config) for column_info in page_info["columns"]}


def get_column_hocr(column_info, config):
    hocr_page = make_hocr_page(column_info["filepath"], column_info["column_id"], config=config)
    column_hocr = hocr_page.carea
    column_hocr["lines"] = hocr_page.lines
    if "remove_tiny_words" in config and config["remove_tiny_words"]:
        column_hocr["lines"] = filter_tiny_words_from_lines(hocr_page, config)
    column_hocr["num_lines"] = len(column_hocr["lines"])
    column_hocr["num_words"] = len([word for line in column_hocr["lines"] for word in line["words"]])
    return column_hocr


def determine_scan_type(scan_hocr: object, config: dict) -> list:
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


def get_page_type(page_hocr: object, debug: bool = False) -> str:
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
        column_header_line = base_parser.get_column_header_line(column_hocr)
        if not column_header_line:
        #    print("\t\tNO HEADER LINE for column id", column_hocr["column_id"])
            continue
        resolution_score += resolution_parser.score_resolution_header(column_header_line, debug=debug)
        index_score += index_parser.score_index_header(column_header_line, column_hocr, debug=debug)
    if page_hocr["num_words"] > 700:
        resolution_score += int(page_hocr["num_words"] / 100)
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
    if base_parser.calculate_left_jumps(page_hocr) < 0.3:
        resolution_score += (1 - base_parser.calculate_left_jumps(page_hocr)) * 10
        if (debug):
            print("\tfew left jumps")
    elif base_parser.calculate_left_jumps(page_hocr) > 0.5:
        if (debug):
            print("\tmany left jumps")
        index_score += base_parser.calculate_left_jumps(page_hocr) * 10
    text = " ".join([line["line_text"] for column in page_hocr["columns"] for line in column["lines"]])
    phrase_matches = fuzzy_searcher.find_candidates(text)
    if phrase_matches:
        resolution_score += len(phrase_matches)
        if debug:
            print("\tresolution phrase matches:", len(phrase_matches))
    if debug:
        print("res_score:", resolution_score, "ind_score:", index_score)
        print(" ".join(base_parser.get_page_header_words(page_hocr)))
    if resolution_score >= 5 and resolution_score > index_score:
        return "resolution_page"
    elif index_score >= 10 and index_score > resolution_score:
        return "index_page"
    else:
        return "unknown_page_type"


def make_page_doc(page_id: str, pages_info: dict, config: dict) -> object:
    page_doc = {}
    for prop in pages_info[page_id]:
        if prop is "columns":
            page_doc["columns"] = []
            for column_info in pages_info[page_id]["columns"]:
                try:
                    column_hocr = get_column_hocr(column_info, config)
                    page_doc["columns"] += [column_hocr]
                except TypeError:
                    print("Error parsing file", column_info["filepath"])
            page_doc["num_columns"] = len(page_doc["columns"])
            page_doc["num_lines"] = max([column_hocr["num_lines"] for column_hocr in page_doc["columns"]])
            page_doc["num_words"] = sum([column_hocr["num_words"] for column_hocr in page_doc["columns"]])
        else:
            page_doc[prop] = pages_info[page_id][prop]
    return page_doc


def initialize_pages_hocr(dp_hocr: dict) -> tuple:
    odd_page_hocr = {"page_id": "year-{}-scan-{}-odd".format(dp_hocr["inventory_year"], dp_hocr["scan_num"]),
                     "page_num": dp_hocr["scan_num"] * 2 - 1, "page_side": "odd",
                     "lines": [], "hocr_box": copy.copy(dp_hocr["hocr_box"])}
    even_page_hocr = {"page_id": "year-{}-scan-{}-even".format(dp_hocr["inventory_year"], dp_hocr["scan_num"]),
                      "page_num": dp_hocr["scan_num"] * 2, "page_side": "even",
                      "lines": [], "hocr_box": copy.copy(dp_hocr["hocr_box"])}
    odd_page_hocr["hocr_box"]["right"] = dp_hocr["page_boundary"] + 100
    even_page_hocr["hocr_box"]["left"] = dp_hocr["page_boundary"] - 100
    scan_props = ["scan_num", "scan_type", "filepath", "inventory_num", "inventory_year", "inventory_period"]
    for scan_prop in scan_props:
        if scan_prop in dp_hocr:
            odd_page_hocr[scan_prop] = dp_hocr[scan_prop]
            even_page_hocr[scan_prop] = dp_hocr[scan_prop]
    return odd_page_hocr, even_page_hocr


def split_lines_on_pages(dp_hocr: dict, columns_info: list, column_config: dict) -> list:
    odd_page_hocr, even_page_hocr = initialize_pages_hocr(dp_hocr)
    for line in dp_hocr["lines"]: # split line on page boundary
        odd_page_words = [word for word in line["words"] if word["right"] < dp_hocr["page_boundary"]]
        even_page_words = [word for word in line["words"] if word["left"] > dp_hocr["page_boundary"]]
        if len(odd_page_words) > 0:
            odd_page_hocr["lines"] += [column_parser.construct_line_from_words(odd_page_words)]
        if len(even_page_words) > 0:
            even_page_hocr["lines"] += [column_parser.construct_line_from_words(even_page_words)]
    return [odd_page_hocr, even_page_hocr]


def parse_double_page_scan(scan_hocr: dict, column_config: dict):
    column_config = copy.copy(column_config)
    column_config["hocr_box"] = scan_hocr["hocr_box"]
    scan_hocr["page_boundary"] = int(scan_hocr["hocr_box"]["right"] / 2)
    columns_info = column_parser.determine_column_start_end(scan_hocr, column_config)
    single_pages_hocr = split_lines_on_pages(scan_hocr, columns_info, column_config)
    for single_page_hocr in single_pages_hocr:
        single_page_hocr["is_parseable"] = True
        columns_hocr = parse_single_page(single_page_hocr, column_config)
        if single_page_hocr["num_columns"] == 0:
            single_page_hocr["num_lines"] = 0
            single_page_hocr["num_words"] = 0
            single_page_hocr["columns"] = []
        else:
            single_page_hocr["columns"] = columns_hocr["columns"]
            single_page_hocr["num_lines"] = max([column["num_lines"] for column in single_page_hocr["columns"]])
            single_page_hocr["num_words"] = sum([column["num_words"] for column in single_page_hocr["columns"]])
        del single_page_hocr["lines"]
        single_page_hocr["page_type"] += [get_page_type(single_page_hocr, debug=False)]
    return single_pages_hocr


def parse_single_page(sp_hocr, column_config: dict):
    column_config["hocr_box"] = sp_hocr["hocr_box"]
    columns_info = column_parser.determine_column_start_end(sp_hocr, column_config)
    sp_hocr["num_columns"] = len(columns_info)
    if sp_hocr["num_columns"] == 0:
        sp_hocr["page_type"] = ["special", "no_column"]
        return sp_hocr
    elif sp_hocr["num_columns"] == 2:
        sp_hocr["page_type"] = ["normal", "double_column"]
    elif sp_hocr["num_columns"] == 1:
        sp_hocr["page_type"] = ["special", "single_column"]
    else:
        sp_hocr["page_type"] = ["special", "multi_column"]
    #print(columns_info)
    return column_parser.split_lines_on_columns(sp_hocr, columns_info, column_config)


