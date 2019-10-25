from elasticsearch import Elasticsearch
import json
import copy

es = Elasticsearch()

def create_es_page_doc(page_doc):
    doc = copy.deepcopy(page_doc)
    for column_doc in doc["columns"]:
        if "column_hocr" in column_doc:
            column_doc["column_hocr"] = json.dumps(column_doc["column_hocr"])
    return doc

def parse_es_page_doc(page_doc):
    for column_doc in page_doc["columns"]:
        if "column_hocr" in column_doc:
            column_doc["column_hocr"] = json.loads(column_doc["column_hocr"])
    return page_doc

def retrieve_page_doc(page_id, config):
    if not es.exists(index=config["page_index"], doc_type=config["page_doc_type"], id=page_id):
        return None
    response = es.get(index=config["page_index"], doc_type=config["page_doc_type"], id=page_id)
    if "_source" in response:
        page_doc = parse_es_page_doc(response["_source"])
        return page_doc
    else:
        return None

def retrieve_paragraph_by_type_page_number(page_number, config):
    query = {"query": {"match": {"metadata.type_page_num": page_number}}, "size": 100}
    response = es.search(index=config["paragraph_index"], doc_type=config["paragraph_doc_type"], body=query)
    if response["hits"]["total"] == 0:
        return []
    else:
        return [hit["_source"] for hit in response["hits"]["hits"]]

def delete_es_index(index):
    if es.indices.exists(index=index):
        print("exists, deleting")
        es.indices.delete(index=index)



