from typing import Union
from elasticsearch import Elasticsearch
import json
import copy

es = Elasticsearch()


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
            column_hocr["lines"] = json.loads(column_hocr["lines"])
    return page_doc


def retrieve_page_doc(page_id: str, config) -> Union[dict, None]:
    if not es.exists(index=config["page_index"], doc_type=config["page_doc_type"], id=page_id):
        return None
    response = es.get(index=config["page_index"], doc_type=config["page_doc_type"], id=page_id)
    if "_source" in response:
        page_doc = parse_es_page_doc(response["_source"])
        return page_doc
    else:
        return None


def retrieve_paragraph_by_type_page_number(page_number: int, config: dict) -> list:
    query = {"query": {"match": {"metadata.type_page_num": page_number}}, "size": 100}
    response = es.search(index=config["paragraph_index"], doc_type=config["paragraph_doc_type"], body=query)
    if response["hits"]["total"] == 0:
        return []
    else:
        return [hit["_source"] for hit in response["hits"]["hits"]]


def delete_es_index(index: str):
    if es.indices.exists(index=index):
        print("exists, deleting")
        es.indices.delete(index=index)
