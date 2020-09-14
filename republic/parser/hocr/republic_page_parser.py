import copy
import json
from typing import Union

from republic.parser.hocr.generic_hocr_parser import make_hocr_doc, filter_tiny_words_from_lines
import republic.parser.hocr.republic_base_page_parser as base_parser
import republic.parser.hocr.republic_index_page_parser as index_parser
import republic.parser.hocr.republic_respect_page_parser as respect_parser
import republic.parser.hocr.republic_resolution_page_parser as resolution_parser
import republic.parser.hocr.republic_column_parser as column_parser
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


def get_page_columns_hocr(page_info: dict, config: dict) -> dict:
    return {column_info["column_id"]: get_column_hocr(column_info, config) for column_info in page_info["columns"]}


def get_column_hocr(column_info: dict, config: dict) -> Union[dict, None]:
    hocr_doc = make_hocr_doc(column_info["filepath"], doc_id=column_info["column_id"], config=config)
    if not hocr_doc:
        return None
    column_hocr = hocr_doc.carea
    column_hocr["lines"] = hocr_doc.lines
    for line in column_hocr["lines"]:
        # print("num words before:", len(line["words"]))
        line["words"] = column_parser.filter_low_confidence_words(line["words"], config)
        # print("num words after:", len(line["words"]))
        # print(line["line_text"])
    if "remove_tiny_words" in config and config["remove_tiny_words"]:
        column_hocr["lines"] = filter_tiny_words_from_lines(hocr_doc, config)
    column_hocr["num_lines"] = len(column_hocr["lines"])
    column_hocr["num_words"] = len([word for line in column_hocr["lines"] for word in line["words"]])
    return column_hocr


def determine_scan_type(scan_hocr: dict, config: dict) -> list:
    if "normal_scan_width" not in config:
        return ["unknown"]
    if scan_hocr["coords"]["width"] > config["normal_scan_width"] * 1.1:
        return ["special", "extended"]
    elif scan_hocr["coords"]["width"] < config["normal_scan_width"] * 0.9:
        return ["special", "small"]
    else:
        return ["normal", "double_page"]


def get_scan_hocr(scan_info: dict, hocr_data: str = None, config: dict = {}) -> Union[dict, None]:
    hocr_doc = make_hocr_doc(scan_info["filepath"], hocr_data=hocr_data, doc_id=scan_info["scan_num"], config=config)
    if not hocr_doc:
        return None
    scan_hocr = {
        'coords': hocr_doc.carea,
        'metadata': scan_info,
        'textregions': [],
        "doc_type": "scan",
        "ocr_type": config["ocr_type"]
    }
    scan_hocr["metadata"]["scan_type"] = determine_scan_type(scan_hocr, config)
    if "double_page" in scan_hocr["metadata"]["scan_type"]:
        scan_hocr["metadata"]["page_boundary"] = int(scan_hocr["coords"]["right"] / 2)
    scan_hocr["textregions"] = [{"lines": hocr_doc.lines}]
    if "remove_tiny_words" in config and config["remove_tiny_words"]:
        scan_hocr["textregions"] = [{"lines": filter_tiny_words_from_lines(hocr_doc, config)}]
    return scan_hocr


def get_page_type_info(page_hocr: dict, debug: bool = False) -> dict:
    page_type_info = {
        "num_words": page_hocr["num_words"],
        "num_page_ref_lines": index_parser.count_page_ref_lines(page_hocr),
        "num_repeat_symbols": index_parser.count_repeat_symbols_page(page_hocr),
        "left_jump_ratio": base_parser.calculate_left_jumps(page_hocr),
        "phrase_matches": len(fuzzy_searcher.find_candidates(get_page_text(page_hocr))),
        "resolution_header_score": 0,
        "index_header_score": 0,
        "respect_header_score": 0,
    }
    for column_hocr in page_hocr["columns"]:
        column_header_line = base_parser.get_column_header_line(column_hocr)
        if column_header_line:
            continue
        resolution_header_score = resolution_parser.score_resolution_header(column_header_line, debug=debug)
        page_type_info["resolution_header_score"] = resolution_header_score
        index_header_score = index_parser.score_index_header(column_header_line, column_hocr, debug=debug)
        page_type_info["index_header_score"] = index_header_score
    return page_type_info


def get_page_text(page_hocr: dict) -> str:
    return " ".join([line["line_text"] for column in page_hocr["columns"] for line in column["lines"]])


def is_empty_page(page_hocr: dict) -> bool:
    if "num_columns" not in page_hocr:
        return True
    if page_hocr["num_columns"] == 0 or page_hocr["num_lines"] == 0 or page_hocr["num_words"] == 0:
        return True
    if is_noise_word_page(page_hocr):
        return True
    else:
        return False


def is_noise_word_page(page_hocr: dict) -> bool:
    if page_hocr["num_words"] > 50:
        return False
    all_words = base_parser.get_words_above(page_hocr, threshold=4000)
    long_words = [word for word in all_words if len(word["word_text"]) >= 5]
    short_words = [word for word in all_words if len(word["word_text"]) <= 3]
    num_non_words = 0
    for short_word in short_words:
        stopwords = ['de', 'het', 'in', 'een', 'van', 'op', 'er', 'u', 'is', 'der', 'den']
        if short_word["word_text"].lower() not in stopwords:
            num_non_words += 1
    if num_non_words / len(all_words) > 0.6:
        return True
    if len(long_words) < 5:
        return True


def is_section_end_page(page_hocr: dict) -> bool:
    # a page ending a section has few words, concentrated in the top
    if page_hocr["num_words"] > 100:
        return False
    num_top_words = len(base_parser.get_words_above(page_hocr, threshold=800))
    if num_top_words / page_hocr["num_words"] < 0.8:
        return False


def is_section_start_page(page_hocr: dict) -> bool:
    lines = [line for column in page_hocr["columns"] for line in column["lines"]]
    top_third = [line for line in lines if line["bottom"] < 1200]
    num_lines_top = len(top_third)
    num_lines_all = len(lines)
    num_chars_top = sum([len(line["line_text"].replace(" ", "")) for line in top_third])
    num_chars_all = sum([len(line["line_text"].replace(" ", "")) for line in lines])
    lines_fraction = 0
    chars_fraction = 0
    if num_lines_all > 0:
        lines_fraction = round(num_lines_top / num_lines_all, 2)
    if num_chars_all > 0:
        chars_fraction = round(num_chars_top / num_chars_all, 2)
    if 150 < page_hocr["num_words"] < 450 and chars_fraction < 0.15 and lines_fraction < 0.25:
        return True
    else:
        return False


def get_page_type(page_hocr: dict, config: dict, debug: bool = False) -> list:
    page_type = get_single_page_column_type(page_hocr)
    if is_empty_page(page_hocr):
        page_type += ["empty_page"]
    elif respect_parser.is_respect_page(page_hocr, config):
        page_type += ["respect_page"]
    else:
        page_type_info = get_page_type_info(page_hocr, debug=debug)
        resolution_score = resolution_parser.score_resolution_page(page_type_info)
        index_score, index_page_type = index_parser.score_index_page(page_hocr, page_type_info, config)
        # print("index_score:", index_score)
        # print("resolution_score:", resolution_score)
        if debug:
            print(json.dumps(page_type_info, indent=2))
        if debug:
            print("res_score:", resolution_score, "ind_score:", index_score)
            print(" ".join(base_parser.get_page_header_words(page_hocr)))
        if resolution_score >= 5 and resolution_score > index_score:
            page_type += ["resolution_page"]
        elif index_score >= 5 and index_score > resolution_score:
            page_type += ["index_page", index_page_type]
        else:
            page_type += ["unknown_page_type"]
    if base_parser.is_title_page(page_hocr, config["title_page"]):
        page_type += ["title_page"]
    if is_section_start_page(page_hocr):
        page_type += ["section_start"]
        if "title_page" not in page_type:
            page_type += ["title_page"]
    return page_type


def make_page_doc(page_id: str, pages_info: dict, config: dict) -> dict:
    page_doc = {"doc_type": "page", "ocr_type": config["ocr_type"]}
    for prop in pages_info[page_id]:
        if prop == "columns":
            page_doc["columns"] = []
            for column_info in pages_info[page_id]["columns"]:
                try:
                    column_hocr = get_column_hocr(column_info, config)
                    if column_hocr:
                        page_doc["columns"] += [column_hocr]
                except TypeError:
                    print("Error parsing file", column_info["filepath"])
            page_doc["num_columns"] = len(page_doc["columns"])
            page_doc["num_lines"] = max([column_hocr["num_lines"] for column_hocr in page_doc["columns"]])
            page_doc["num_words"] = sum([column_hocr["num_words"] for column_hocr in page_doc["columns"]])
        else:
            page_doc[prop] = pages_info[page_id][prop]
    return page_doc


def initialize_page_hocr(dp_hocr: dict, config: dict) -> dict:
    return {
        'metadata': dp_hocr['metadata'],
        'doc_type': 'page',
        'ocr_type': config['ocr_type'],
        "coords": {},
        "textregions": [{"lines": []}]
    }


def initialize_page_side_hocr(dp_hocr: dict, config: dict, side: str) -> dict:
    if side not in ["even", "odd"]:
        raise ValueError('side must be even or odd')
    page_hocr = initialize_page_hocr(dp_hocr, config)
    if side == "even":
        page_num = dp_hocr["metadata"]["scan_num"] * 2 - 2
    else:
        page_num = dp_hocr["metadata"]["scan_num"] * 2 - 1
    page_hocr["metadata"]["page_side"] = side
    page_hocr["metadata"]["page_id"] = f"{dp_hocr['metadata']['scan_id']}-page-{page_num}"
    page_hocr["metadata"]["page_num"] = page_num
    return page_hocr


def initialize_pages_hocr(dp_hocr: dict, config: dict) -> tuple:
    even_page_hocr = initialize_page_side_hocr(dp_hocr, config, "even")
    odd_page_hocr = initialize_page_side_hocr(dp_hocr, config, "even")
    box_items = ["width", "height", "left", "right", "top", "bottom"]
    for box_item in box_items:
        even_page_hocr["coords"][box_item] = dp_hocr["coords"][box_item]
        odd_page_hocr["coords"][box_item] = dp_hocr["coords"][box_item]
    even_page_hocr["coords"]["right"] = dp_hocr["metadata"]["page_boundary"] + 100
    odd_page_hocr["coords"]["left"] = dp_hocr["metadata"]["page_boundary"] - 100
    return even_page_hocr, odd_page_hocr


def split_lines_on_pages(dp_hocr: dict) -> list:
    even_page_hocr, odd_page_hocr = initialize_pages_hocr(dp_hocr)
    for line in dp_hocr["textregions"][0]["lines"]:
        # split line on page boundary
        even_page_words = [word for word in line["words"] if word["right"] < dp_hocr["page_boundary"]]
        odd_page_words = [word for word in line["words"] if word["left"] > dp_hocr["page_boundary"]]
        if len(even_page_words) > 0:
            even_page_hocr["textregions"][0]["lines"] += [column_parser.construct_line_from_words(even_page_words)]
        if len(odd_page_words) > 0:
            odd_page_hocr["textregions"][0]["lines"] += [column_parser.construct_line_from_words(odd_page_words)]
    return [even_page_hocr, odd_page_hocr]


def parse_double_page_scan(scan_hocr: dict, config: dict):
    config = copy.copy(config)
    scan_hocr["metadata"]["page_boundary"] = int(scan_hocr["coords"]["right"] / 2)
    # column_parser.determine_column_start_end(scan_hocr, config)
    single_pages_hocr = split_lines_on_pages(scan_hocr)
    for single_page_hocr in single_pages_hocr:
        parse_single_page(single_page_hocr, config)
    return single_pages_hocr


def get_single_page_column_type(sp_hocr: dict):
    if "num_columns" not in sp_hocr or sp_hocr["num_columns"] == 0:
        return ["special", "no_column"]
    elif sp_hocr["num_columns"] == 2:
        return ["normal", "double_column"]
    elif sp_hocr["num_columns"] == 1:
        return ["special", "single_column"]
    else:
        return ["special", "multi_column"]


def parse_single_page(single_page_hocr: dict, config: dict):
    # config["hocr_box"] = single_page_hocr["hocr_box"]
    page_columns_info = column_parser.determine_column_start_end(single_page_hocr, config)
    columns_hocr = column_parser.split_lines_on_columns(single_page_hocr, page_columns_info, config)
    # print(page_columns_info)
    metadata = single_page_hocr["metadata"]
    metadata["num_columns"] = len(page_columns_info)
    metadata["is_parseable"] = True
    if metadata["num_columns"] == 0:
        metadata["num_lines"] = 0
        metadata["num_words"] = 0
        metadata["columns"] = []
    else:
        single_page_hocr["textregions"] = columns_hocr["textregions"]
        metadata["num_lines"] = max([column["num_lines"] for column in single_page_hocr["textregions"]])
        metadata["num_words"] = sum([column["num_words"] for column in single_page_hocr["textregions"]])
    metadata["page_type"] = get_page_type(single_page_hocr, config)
    metadata["is_title_page"] = True if "title_page" in metadata["page_type"] else False
