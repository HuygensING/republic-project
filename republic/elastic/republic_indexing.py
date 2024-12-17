from typing import Union, Dict, List
import datetime
import copy
import time

from elasticsearch import Elasticsearch
from elasticsearch.exceptions import ElasticsearchException
from elasticsearch.helpers import bulk
from fuzzy_search.match.phrase_match import PhraseMatch

import republic.model.republic_document_model as rdm
import republic.model.physical_document_model as pdm
from republic.helper.metadata_helper import get_per_page_type_index
from republic.helper.annotation_helper import make_match_hash_id
from republic.helper.utils import get_iso_utc_timestamp, get_commit_url


def add_timestamp(doc: Union[Dict[str, any], pdm.StructureDoc]) -> None:
    if isinstance(doc, dict) and 'type' in doc and doc['type'] == 'session':
        doc['index_timestamp'] = get_iso_utc_timestamp()
    elif isinstance(doc, pdm.StructureDoc) or hasattr(doc, 'metadata'):
        doc.metadata['index_timestamp'] = get_iso_utc_timestamp()
    elif "metadata" not in doc and "inventory_uuid" in doc:
        # datetime.datetime.now().isoformat()
        doc["index_timestamp"] = get_iso_utc_timestamp()
    elif isinstance(doc, dict):
        doc['metadata']['index_timestamp'] = get_iso_utc_timestamp()
    else:
        raise TypeError(f"doc must be a StructureDoc or a dict, not {type(doc)}")


def add_commit(doc: Union[Dict[str, any], pdm.StructureDoc]) -> None:
    if isinstance(doc, dict) and 'type' in doc and doc['type'] == 'session':
        doc['code_commit'] = get_commit_url()
    elif isinstance(doc, pdm.StructureDoc) or hasattr(doc, 'metadata'):
        doc.metadata['code_commit'] = get_commit_url()
    elif "metadata" not in doc and "inventory_uuid" in doc:
        # datetime.datetime.now().isoformat()
        doc["code_commit"] = get_commit_url()
    elif isinstance(doc, dict):
        doc['metadata']['code_commit'] = get_commit_url()
    else:
        raise TypeError(f"doc must be a StructureDoc or a dict, not {type(doc)}")


def check_resolution(resolution: rdm.Resolution):
    """Make sure the resolution contains the all the necessary data."""
    if 'proposition_type' not in resolution.metadata or resolution.metadata['proposition_type'] is None:
        resolution.metadata['proposition_type'] = 'onbekend'


def get_pagexml_page_type(page: Union[pdm.PageXMLPage, Dict[str, any]],
                          page_type_index: Dict[int, Union[str, List[str]]]) -> str:
    page_num = page.metadata['page_num'] if isinstance(page, pdm.PageXMLPage) else page['metadata']['page_num']
    if page_num not in page_type_index:
        return "empty_page"
    else:
        return page_type_index[page_num]


def normalize_lemma(lemma: str) -> str:
    lemma = lemma.replace(' ', '_').replace('/', '_').replace('ê', 'e')
    return lemma


class Indexer:

    def __init__(self, es_anno: Elasticsearch, es_text: Elasticsearch, config: dict):
        self.es_anno = es_anno
        self.es_text = es_text
        self.config = config

    def index_doc(self, index: str, doc_id: str, doc_body: dict, max_retries: int = 5):
        add_timestamp(doc_body)
        add_commit(doc_body)
        retry_num = 0
        while retry_num < max_retries:
            try:
                if self.config["es_api_version"][0] <= 7 and self.config["es_api_version"][1] < 15:
                    response = self.es_anno.index(index=index, id=doc_id, body=doc_body)
                else:
                    response = self.es_anno.index(index=index, id=doc_id, document=doc_body)
                return response
            except ElasticsearchException as err:
                if 'stats' in doc_body:
                    print(f"Error indexing document {doc_id} with stats {doc_body['stats']}, retry {retry_num}")
                else:
                    print(f"Error indexing document {doc_id} in index {index}, retry {retry_num}")
                print(err)
                error = err
                time.sleep(5)
            retry_num += 1
            if retry_num >= max_retries:
                raise error

    def index_bulk_docs(self, index: str, docs: List[Dict[str, any]], max_retries: int = 5) -> None:
        actions = []
        for doc in docs:
            add_timestamp(doc)
            add_commit(doc)
            action = {
                '_index': index,
                '_id': doc['id'],
                '_source': doc
            }
            actions.append(action)
        try_num = 0
        while try_num < max_retries:
            try:
                bulk(self.es_anno, actions)
                break
            except ElasticsearchException:
                print(f"Error bulk indexing documents")
                for doc in docs:
                    print(f"\t{doc['id']} with stats {doc['stats']}")
                print(f"retry {try_num}")
                time.sleep(5)
                if try_num >= max_retries:
                    raise
                try_num += 1

    def index_scan(self, scan: pdm.PageXMLScan):
        if 'inventory_id' not in scan.metadata:
            scan.metadata['inventory_id'] = f"{scan.metadata['series_name']}_{scan.metadata['inventory_num']}"
        self.index_doc(index=self.config['scans_index'], doc_id=scan.id, doc_body=scan.json)

    def index_page(self, page: pdm.PageXMLPage):
        self.index_doc(index=self.config['pages_index'], doc_id=page.id, doc_body=page.json)

    def index_inventory_metadata(self, inventory_metadata: dict):
        if "created" not in inventory_metadata:
            inventory_metadata["created"] = datetime.datetime.now().isoformat()
        else:
            inventory_metadata["updated"] = datetime.datetime.now().isoformat()
        self.index_doc(index=self.config['inventory_index'],
                       doc_id=inventory_metadata['inventory_num'],
                       doc_body=inventory_metadata)

    def index_session_with_lines(self, session: rdm.Session):
        self.index_doc(index=self.config['session_lines_index'],
                       doc_id=session.id,
                       doc_body=session.json)

    def index_session_with_text(self, session_text_doc: dict):
        self.index_doc(index=self.config['session_text_index'],
                       doc_id=session_text_doc["metadata"]["id"],
                       doc_body=session_text_doc)

    def index_session_metadata(self, metadata: dict):
        self.index_doc(index=self.config['session_metadata_index'],
                       doc_id=metadata['id'],
                       doc_body=metadata)

    def index_session_text_region(self, session_tr: pdm.PageXMLTextRegion):
        self.index_doc(index=self.config['session_text_region_index'],
                       doc_id=session_tr.id,
                       doc_body=session_tr.json)

    def index_session_text_regions(self, session_trs: List[pdm.PageXMLTextRegion]):
        trs_json = [tr.json for tr in session_trs]
        self.index_bulk_docs(self.config['session_text_region_index'], trs_json)
        # self.index_doc(index=self.config['session_text_region_index'],
        #                doc_id=session_tr.id,
        #                doc_body=session_tr.json)

    def index_resolution(self, resolution: rdm.Resolution):
        check_resolution(resolution)
        print('\t', resolution.id, resolution.paragraphs[0].text[:60])
        self.index_doc(index=self.config['resolutions_index'],
                       doc_id=resolution.metadata['id'],
                       doc_body=resolution.json)

    def index_attendance_list(self, attendance_list: rdm.AttendanceList):
        self.index_doc(index=self.config["resolutions_index"],
                       doc_id=attendance_list.id,
                       doc_body=attendance_list.json)

    def index_resolution_metadata(self, resolution: rdm.Resolution):
        metadata_copy: Dict[str, any] = copy.deepcopy(resolution.metadata)
        metadata_doc = {
            'metadata': metadata_copy,
            'evidence': [pm.json() for pm in resolution.evidence]
        }
        if not metadata_doc['metadata']['id'].endswith('-metadata'):
            metadata_doc['metadata']['id'] = metadata_doc['metadata']['id'] + '-metadata'
        print('indexing metadata for resolution', metadata_doc['metadata']['id'])
        self.index_doc(index=self.config['resolution_metadata_index'],
                       doc_id=metadata_doc['metadata']['id'],
                       doc_body=metadata_doc)

    def index_resolution_phrase_match(self, phrase_match: Union[dict, PhraseMatch],
                                      resolution: rdm.Resolution):
        # make sure match object is json dictionary
        match_json = phrase_match.json() if isinstance(phrase_match, PhraseMatch) else phrase_match
        # generate stable id based on match offset, end and text_id
        match_json['id'] = make_match_hash_id(match_json)
        match_json['metadata'] = phrase_match.phrase.metadata
        match_json['metadata']['id'] = match_json['id']
        match_json['metadata']['resolution_id'] = resolution.id
        match_json['metadata']['session_id'] = resolution.metadata['session_id']
        match_json['metadata']['paragraph_id'] = phrase_match.text_id
        add_timestamp(match_json)
        # print(json.dumps(match_json, indent=2))
        self.index_doc(index=self.config['phrase_matches_index'],
                       doc_id=match_json['id'],
                       doc_body=match_json)

    def index_lemma_reference(self, lemma_reference):
        self.index_doc(index=self.config['lemma_index'],
                       doc_id=lemma_reference["id"],
                       doc_body=lemma_reference)

    def add_pagexml_page_types(self, inv_metadata: dict,
                               pages: List[pdm.PageXMLPage]) -> None:
        page_type_index = get_per_page_type_index(inv_metadata)
        for pi, page in enumerate(sorted(pages, key=lambda x: x.metadata['page_num'])):
            page.metadata['page_type'] = get_pagexml_page_type(page, page_type_index)
            self.index_page(page)
            print(page.metadata['id'], page.metadata["page_type"])

    def delete_resolution_phrase_match(self, phrase_match: Union[dict, PhraseMatch]):
        # make sure match object is json dictionary
        match_json = phrase_match.json() if isinstance(phrase_match, PhraseMatch) else phrase_match
        # generate stable id based on match offset, end and text_id
        match_json['id'] = make_match_hash_id(match_json)
        if self.es_anno.exists(index=self.config['phrase_matches_index'], id=match_json['id']):
            self.es_anno.delete(index=self.config['phrase_matches_index'], id=match_json['id'])
        else:
            raise ValueError(f'unknown phrase match id {match_json["id"]}, phrase match cannot be removed')

    def delete_es_index(self, index: str):
        if self.es_anno.indices.exists(index=index):
            print(f' index{index} exists, deleting')
            print(self.es_anno.indices.delete(index=index))

    def delete_by_query(self, index: str, query: Dict[str, any]):
        if self.es_anno.indices.exists(index=index) is False:
            raise ValueError(f"index {index} does not exist")
        response = self.es_anno.delete_by_query(index, query)
        # response = self.rep_es.delete_by_inventory(index, inv_num=inv_metadata['inventory_num'])
        print(f'ES response: {response}\n')
        return response

    def delete_by_inventory(self, index: str, inv_num: int = None, inv_id: str = None):
        if self.es_anno.indices.exists(index=index) is False:
            return None
        if inv_id is not None:
            if isinstance(inv_id, int):
                raise TypeError("inv_id must be str, not int")
            match = {'metadata.inventory_id.keyword': inv_id}
        elif inv_num is not None:
            if isinstance(inv_num, str):
                raise TypeError("inv_num must be int, not str")
            match = {'metadata.inventory_num': inv_num}
        else:
            raise ValueError(f"must pass either inv_id or inv_num for index {index}")
        query = {'match': match}
        response = self.es_anno.search(index=index, query=query, size=0)
        print(f"search with delete_by_query query has returned {response['hits']['total']['value']} hits")
        query = {'query': query}
        return self.delete_by_query(index, query)

    def block_index(self, index: str):
        print(self.es_anno.indices.put_settings(index=index, body={"index.blocks.write": True}))

    def unblock_index(self, index: str):
        print(self.es_anno.indices.put_settings(index=index, body={"index.blocks.write": False}))

    def clone_index(self, original_index: str, new_index: str, delete_original: bool = False,
                    force: bool = False) -> None:
        # 1. make sure the clone index doesn't exist
        if self.es_anno.indices.exists(index=new_index):
            if force is True:
                print("deleting clone index:", new_index)
                print(self.es_anno.indices.delete(index=new_index))
            else:
                raise ValueError("index already exists")
        # 2. set original index to read-only
        print(f"setting original index {original_index} to read-only")
        print(self.es_anno.indices.put_settings(index=original_index, body={"index.blocks.write": True}))
        # 3. clone the index
        print(f"cloning original index {original_index} to {new_index}")
        print(self.es_anno.indices.clone(index=original_index, target=new_index))
        # 4. set original index to read-write
        if delete_original is True:
            print(f"deleting original index {original_index}")
            print(self.es_anno.indices.delete(index=original_index))
        else:
            print(f"setting original index {original_index} to read-write")
            print(self.es_anno.indices.put_settings(index=original_index, body={"index.blocks.write": False}))
            print(self.es_anno.indices.put_settings(index=original_index,
                                                    body={"index.blocks.read_only_allow_delete": False}))
        print(f"setting new index {original_index} to read-write")
        print(self.es_anno.indices.put_settings(index=new_index, body={"index.blocks.write": False}))
        print(self.es_anno.indices.put_settings(index=new_index, body={"index.blocks.read_only_allow_delete": False}))
