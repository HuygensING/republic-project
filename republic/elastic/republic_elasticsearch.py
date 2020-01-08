from typing import Union, List, Dict
from elasticsearch import Elasticsearch
import json
import copy
import os
import zipfile
from republic.config.republic_config import set_config_inventory_num
from republic.fuzzy.fuzzy_context_searcher import FuzzyContextSearcher
from republic.model.republic_hocr_model import HOCRPage
from republic.model.republic_phrase_model import category_index
import republic.parser.republic_base_page_parser as base_parser
import republic.parser.republic_file_parser as file_parser
import republic.parser.republic_page_parser as page_parser
import republic.parser.republic_paragraph_parser as para_parser
from settings import config


def initialize_es() -> Elasticsearch:
    es_config = config["elastic_config"]
    if es_config["url_prefix"]:
        es_republic = Elasticsearch(
            [{"host": es_config["host"], "port": es_config["port"], "url_prefix": es_config["url_prefix"]}])
    else:
        es_republic = Elasticsearch([{"host": es_config["host"], "port": es_config["port"]}])
    return es_republic


def scroll_hits(es: Elasticsearch, query: dict, index: str, doc_type: str, size: int = 100) -> iter:
    response = es.search(index=index, doc_type=doc_type, scroll='2m', size=size, body=query)
    sid = response['_scroll_id']
    scroll_size = response['hits']['total']
    if type(scroll_size) == dict:
        scroll_size = scroll_size["value"]
    # Start scrolling
    while scroll_size > 0:
        for hit in response['hits']['hits']:
            yield hit
        response = es.scroll(scroll_id=sid, scroll='2m')
        # Update the scroll ID
        sid = response['_scroll_id']
        # Get the number of results that we returned in the last scroll
        scroll_size = len(response['hits']['hits'])
        # Do something with the obtained page


def create_es_scan_doc(scan_doc: dict) -> dict:
    doc = copy.deepcopy(scan_doc)
    if "lines" in doc:
        doc["lines"] = json.dumps(doc["lines"])
    return doc


def create_es_page_doc(page_doc: dict) -> dict:
    doc = copy.deepcopy(page_doc)
    for column_hocr in doc["columns"]:
        if "lines" in column_hocr:
            column_hocr["lines"] = json.dumps(column_hocr["lines"])
    return doc


def parse_es_scan_doc(scan_doc: dict) -> dict:
    if "lines" in scan_doc:
        scan_doc["lines"] = json.loads(scan_doc["lines"])
    return scan_doc


def parse_es_page_doc(page_doc: dict) -> dict:
    for column_hocr in page_doc["columns"]:
        if "lines" in column_hocr:
            if isinstance(column_hocr["lines"], str):
                column_hocr["lines"] = json.loads(column_hocr["lines"])
    return page_doc


def parse_hits_as_pages(hits: dict) -> List[dict]:
    return [parse_es_page_doc(hit["_source"]) for hit in hits]


def make_bool_query(match_fields, size: int = 10000) -> dict:
    return {
        "query": {
            "bool": {
                "must": match_fields
            }
        },
        "size": size
    }


def make_column_query(num_columns_min: int, num_columns_max: int, inventory_num: int) -> dict:
    match_fields = [
        {"match": {"inventory_num": inventory_num}},
        {
            "range": {
                "num_columns": {
                    "gte": num_columns_min,
                    "lte": num_columns_max
                }
            }
        }
    ]
    return make_bool_query(match_fields)


def make_page_type_query(page_type: str, year: Union[int, None] = None,
                         inventory_num: Union[int, None] = None,
                         size: int = 10000) -> dict:
    match_fields = [{"match": {"page_type": page_type}}]
    if inventory_num: match_fields += [{"match": {"inventory_num": inventory_num}}]
    if year: match_fields += [{"match": {"year": year}}]
    return make_bool_query(match_fields, size)


def retrieve_inventory_metadata(es: Elasticsearch, inventory_num: int, config):
    if not es.exists(index=config["inventory_index"], doc_type=config["inventory_doc_type"], id=inventory_num):
        raise ValueError("No inventory metadata available for inventory num {}".format(inventory_num))
    response = es.get(index=config["inventory_index"], doc_type=config["inventory_doc_type"], id=inventory_num)
    return response["_source"]


def retrieve_page_doc(es: Elasticsearch, page_id: str, config) -> Union[dict, None]:
    if not es.exists(index=config["page_index"], doc_type=config["page_doc_type"], id=page_id):
        return None
    response = es.get(index=config["page_index"], doc_type=config["page_doc_type"], id=page_id)
    if "_source" in response:
        page_doc = parse_es_page_doc(response["_source"])
        return page_doc
    else:
        return None


def retrieve_pages_with_query(es: Elasticsearch, query: dict, config: dict) -> list:
    response = es.search(index=config["page_index"], body=query)
    if response['hits']['total'] == 0:
        return []
    return parse_hits_as_pages(response['hits']['hits'])


def retrieve_page_by_page_number(es: Elasticsearch, page_num: int, config: dict) -> dict:
    match_fields = [{"match": {"page_num": page_num}}]
    if "inventory_num" in config: match_fields += [{"match": {"inventory_num": config["inventory_num"]}}]
    elif "year" in config: match_fields += [{"match": {"year": config["year"]}}]
    query = make_bool_query(match_fields)
    pages = retrieve_pages_with_query(es, query, config)
    if len(pages) == 0:
        return None
    else:
        return pages[0]


def retrieve_pages_by_type(es: Elasticsearch, page_type: str, inventory_num: int, config: dict) -> List[dict]:
    query = make_page_type_query(page_type, inventory_num=inventory_num)
    return retrieve_pages_with_query(es, query, config)


def retrieve_pages_by_number_of_columns(es: Elasticsearch, num_columns_min: int,
                                        num_columns_max: int, inventory_config: dict) -> list:
    query = make_column_query(num_columns_min, num_columns_max, inventory_config["inventory_num"])
    return retrieve_pages_with_query(es, query, inventory_config)


def retrieve_title_pages(es: Elasticsearch, inventory_num: int, config: dict) -> list:
    return retrieve_pages_by_type(es, "title_page", inventory_num, config)


def retrieve_index_pages(es: Elasticsearch, inventory_num: int, config: dict) -> list:
    return retrieve_pages_by_type(es, "index_page", inventory_num, config)


def retrieve_resolution_pages(es: Elasticsearch, inventory_num: int, config: dict) -> list:
    return retrieve_pages_by_type(es, "resolution_page", inventory_num, config)


def retrieve_respect_pages(es: Elasticsearch, inventory_num: int, config: dict) -> list:
    return retrieve_pages_by_type(es, "respect_page", inventory_num, config)


def retrieve_paragraph_by_type_page_number(es: Elasticsearch, page_number: int, config: dict) -> list:
    match_fields = [
        {"match": {"metadata.type_page_num": page_number}},
        {"match": {"metadata.inventory_year": config["year"]}}
    ]
    query = make_bool_query(match_fields)
    response = es.search(index=config["paragraph_index"], doc_type=config["paragraph_doc_type"], body=query)
    if response["hits"]["total"] == 0:
        return []
    else:
        return [hit["_source"] for hit in response["hits"]["hits"]]


def delete_es_index(es: Elasticsearch, index: str):
    if es.indices.exists(index=index):
        print("exists, deleting")
        es.indices.delete(index=index)


def index_inventory_metadata(es: Elasticsearch, inventory_metadata: dict, config: dict):
    es.index(index=config["inventory_index"], doc_type=config["inventory_doc_type"],
             id=inventory_metadata["inventory_num"], body=inventory_metadata)


def index_scan(es: Elasticsearch, scan_hocr: dict, config: dict):
    doc = create_es_scan_doc(scan_hocr)
    es.index(index=config["scan_index"], doc_type=config["scan_doc_type"], id=scan_hocr["scan_id"], body=doc)


def index_page(es: Elasticsearch, page_hocr: dict, config: dict):
    doc = create_es_page_doc(page_hocr)
    es.index(index=config["page_index"], doc_type=config["page_doc_type"], id=page_hocr["page_id"], body=doc)


def parse_hocr_inventory_from_zip(es: Elasticsearch, inventory_num: int, base_config: dict, base_dir: str):
    inventory_config = set_config_inventory_num(base_config, inventory_num, base_dir)
    hocr_dir = os.path.join(base_dir, "hocr")
    inv_file = os.path.join(hocr_dir, f"{inventory_num}.zip")
    z = zipfile.ZipFile(inv_file)
    for scan_file in z.namelist():
        scan_info = file_parser.get_scan_info(scan_file, inventory_config["hocr_dir"])
        with z.open(scan_file) as fh:
            scan_data = fh.read()
            scan_hocr = page_parser.get_scan_hocr(scan_info, scan_data=scan_data, config=inventory_config)
            if "double_page" in scan_hocr["scan_type"]:
                pages_hocr = page_parser.parse_double_page_scan(scan_hocr, inventory_config)
                for page_hocr in pages_hocr:
                    print(inventory_num, "indexing page", page_hocr["page_id"])
                    #index_page(es, page_hocr, inventory_config)
            else:
                print("indexing scan")
                #index_scan(es, scan_hocr, inventory_config)
                continue


def parse_hocr_inventory(es: Elasticsearch, inventory_num: int, base_config: dict, base_dir: str):
    inventory_config = set_config_inventory_num(base_config, inventory_num, base_dir)
    #print(inventory_config)
    scan_files = file_parser.get_files(inventory_config["hocr_dir"])
    for scan_file in scan_files:
        scan_hocr = page_parser.get_scan_hocr(scan_file, config=inventory_config)
        if "double_page" in scan_hocr["scan_type"]:
            #print("double page scan:", scan_hocr["scan_num"], scan_hocr["scan_type"])
            pages_hocr = page_parser.parse_double_page_scan(scan_hocr, inventory_config)
            for page_hocr in pages_hocr:
                #print(inventory_num, page_hocr["page_num"], page_hocr["page_type"])
                index_page(es, page_hocr, inventory_config)
        else:
            #print("NOT DOUBLE PAGE:", scan_hocr["scan_num"], scan_hocr["scan_type"])
            index_scan(es, scan_hocr, inventory_config)
            continue


def parse_pre_split_column_inventory(es: Elasticsearch, pages_info: dict, config: dict, delete_index: bool = False):
    numbering = 0
    if delete_index:
        delete_es_index(es, config["page_index"])
    for page_id in pages_info:
        numbering += 1
        page_doc = page_parser.make_page_doc(page_id, pages_info, config)
        page_doc["num_columns"] = len(page_doc["columns"])
        try:
            page_type = page_parser.get_page_type(page_doc, config, debug=False)
        except TypeError:
            print(json.dumps(page_doc, indent=2))
            raise
        page_doc["page_type"] = page_type
        page_doc["is_parseable"] = True if page_type != "bad_page" else False
        if base_parser.is_title_page(page_doc, config["title_page"]):
            numbering = 1 # reset numbering
            #page_doc["page_type"] += ["title_page"]
            page_doc["is_title_page"] = True
        else:
            page_doc["is_title_page"] = False
        page_doc["type_page_num"] = numbering
        page_doc["type_page_num_checked"] = False
        ##################################
        # DIRTY HACK FOR INVENTORY 3780! #
        if page_doc["page_num"] in [89, 563, 565]:
            if "title_page" not in page_doc["page_type"]:
                page_doc["page_type"] += ["title_page"]
            page_doc["is_title_page"] = True
        ##################################
        page_es_doc = create_es_page_doc(page_doc)
        print(config["inventory_num"], page_doc["page_num"], page_doc["page_type"])
        es.index(index=config["page_index"], doc_type=config["page_doc_type"], id=page_id, body=page_es_doc)
        #print(page_id, page_type, numbering)


def index_paragraphs(es: Elasticsearch, fuzzy_searcher: FuzzyContextSearcher, inventory_num: int, inventory_config: dict):
    current_date = para_parser.initialize_current_date(inventory_config)
    page_docs = retrieve_resolution_pages(es, inventory_num, inventory_config)
    print("Pages retrieved:", len(page_docs), "\n")
    for page_doc in sorted(page_docs, key = lambda x: x["page_num"]):
        hocr_page = HOCRPage(page_doc, inventory_config)
        paragraphs, header = para_parser.get_resolution_page_paragraphs(hocr_page)
        for paragraph_order, paragraph in enumerate(paragraphs):
            matches = fuzzy_searcher.find_candidates(paragraph["text"], include_variants=True)
            if para_parser.matches_resolution_phrase(matches):
                paragraph["metadata"]["type"] = "resolution"
            current_date = para_parser.track_meeting_date(paragraph, matches, current_date, inventory_config)
            paragraph["metadata"]["keyword_matches"] = matches
            for match in matches:
                if match["match_keyword"] in category_index:
                    category = category_index[match["match_keyword"]]
                    match["match_category"] = category
                    paragraph["metadata"]["categories"].add(category)
            paragraph["metadata"]["categories"] = list(paragraph["metadata"]["categories"])
            del paragraph["lines"]
            es.index(index=inventory_config["paragraph_index"], doc_type=inventory_config["paragraph_doc_type"],
                     id=paragraph["metadata"]["paragraph_id"], body=paragraph)



