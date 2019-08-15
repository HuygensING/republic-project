import json
import re
import copy
from parse_hocr_files import make_hocr_page, filter_tiny_words_from_lines
from elasticsearch import Elasticsearch
import republic_elasticsearch as rep_es
import republic_index_page_parser as index_parser
import republic_base_page_parser as page_parser
import republic_resolution_page_parser as resolution_parser

def get_page_columns_hocr(page_info, config):
    return {column_info["column_id"]: get_column_hocr(column_info, config) for column_info in page_info["columns"]}

def get_column_hocr(column_info, config):
    hocr_page = make_hocr_page(column_info["filepath"], column_info["column_id"], config=config)
    column_hocr = hocr_page.carea
    column_hocr["lines"] = hocr_page.lines
    if "remove_tiny_words" in config and config["remove_tiny_words"]:
        column_hocr["lines"] = filter_tiny_words_from_lines(hocr_page, config)
    return column_hocr

def get_page_type(page_info, config, DEBUG=False):
    resolution_score = 0
    index_score = 0
    for column_info in page_info["columns"]:
        if not "column_hocr" in column_info:
            return "bad_page"
        column_hocr = column_info["column_hocr"]
        if not page_parser.proper_column_cut(column_hocr):
            page_type = "bad_page"
            return page_type
        column_header_line = page_parser.get_column_header_line(column_hocr)
        #if not column_header_line:
        #    print("\t\tNO HEADER LINE for column id", column_info["column_id"])
        #    continue
        resolution_score += resolution_parser.score_resolution_header(column_header_line, column_hocr, DEBUG=DEBUG)
        index_score += index_parser.score_index_header(column_header_line, column_hocr, DEBUG=DEBUG)
    if index_parser.count_page_ref_lines(page_info) >= 10:
        index_score += int(index_parser.count_page_ref_lines(page_info) / 10)
        if DEBUG:
            print("\tIndex test - many page references:", index_parser.count_page_ref_lines(page_info))
    if index_parser.count_repeat_symbols_page(page_info) == 0:
        resolution_score += 1
    else:
        index_score += index_parser.count_repeat_symbols_page(page_info)
    if page_parser.calculate_left_jumps(page_info) < 0.3:
        resolution_score += (1 - page_parser.calculate_left_jumps(page_info)) * 10
        if (DEBUG):
            print("\tfew left jumps")
    elif page_parser.calculate_left_jumps(page_info) > 0.5:
        if (DEBUG):
            print("\tmany left jumps")
        index_score += page_parser.calculate_left_jumps(page_info) * 10
    if DEBUG:
        print("res_score:", resolution_score, "ind_score:", index_score)
        print(" ".join(page_parser.get_page_header_words(page_info)))
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
            page_type = get_page_type(page_info, config, DEBUG=False)
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



