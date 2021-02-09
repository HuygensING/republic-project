from typing import Union, List, Dict, Generator
from elasticsearch import Elasticsearch
import json
import copy
from collections import defaultdict

from fuzzy_search.fuzzy_match import PhraseMatch

from republic.helper.metadata_helper import get_scan_id
from republic.model.republic_meeting import Meeting, meeting_from_json
from republic.model.republic_date import RepublicDate
from republic.model.republic_document_model import resolution_from_json, Resolution, parse_phrase_matches
from republic.model.republic_document_model import page_json_to_resolution_page, ResolutionPageDoc
import republic.parser.pagexml.republic_pagexml_parser as pagexml_parser


def scroll_hits(es: Elasticsearch, query: dict, index: str, doc_type: str, size: int = 100,
                scroll: str = '2m') -> iter:
    response = es.search(index=index, doc_type=doc_type, scroll=scroll, size=size, body=query)
    sid = response['_scroll_id']
    scroll_size = response['hits']['total']
    print('total hits:', scroll_size)
    if type(scroll_size) == dict:
        scroll_size = scroll_size['value']
    # Start scrolling
    while scroll_size > 0:
        for hit in response['hits']['hits']:
            yield hit
        response = es.scroll(scroll_id=sid, scroll=scroll)
        # Update the scroll ID
        sid = response['_scroll_id']
        # Get the number of results that we returned in the last scroll
        scroll_size = len(response['hits']['hits'])
        # Do something with the obtained page
    # remove scroll context
    es.clear_scroll(scroll_id=sid)


def create_es_scan_doc(scan_doc: dict) -> dict:
    doc = copy.deepcopy(scan_doc)
    if 'lines' in doc:
        doc['lines'] = json.dumps(doc['lines'])
    return doc


def create_es_page_doc(page_doc: dict) -> dict:
    doc = copy.deepcopy(page_doc)
    for column_hocr in doc['columns']:
        if 'lines' in column_hocr:
            column_hocr['lines'] = json.dumps(column_hocr['lines'])
    return doc


def parse_es_scan_doc(scan_doc: dict) -> dict:
    if 'lines' in scan_doc:
        scan_doc['lines'] = json.loads(scan_doc['lines'])
    return scan_doc


def parse_es_page_doc(page_doc: dict) -> dict:
    for column_hocr in page_doc['columns']:
        if 'lines' in column_hocr:
            if isinstance(column_hocr['lines'], str):
                column_hocr['lines'] = json.loads(column_hocr['lines'])
    return page_doc


def create_es_index_lemma_doc(lemma: str, lemma_index: dict, config: dict):
    return {
        'lemma': lemma,
        'inventory_num': config['inventory_num'],
        'lemma_entries': lemma_index[lemma]
    }


def parse_hits_as_pages(hits: dict) -> List[ResolutionPageDoc]:
    return [page_json_to_resolution_page(hit['_source']) for hit in hits]


def make_bool_query(match_fields, size: int = 10000) -> dict:
    return {
        'query': {
            'bool': {
                'must': match_fields
            }
        },
        'size': size
    }


def make_column_query(num_columns_min: int, num_columns_max: int, inventory_num: int) -> dict:
    match_fields = [
        {'match': {'metadata.inventory_num': inventory_num}},
        {
            'range': {
                'num_columns': {
                    'gte': num_columns_min,
                    'lte': num_columns_max
                }
            }
        }
    ]
    return make_bool_query(match_fields)


def make_range_query(field: str, start: int, end: int):
    return {
        "query": {
            "range": {
                field: {
                    "gte": start,
                    "lte": end
                }
            }
        }
    }


def make_page_type_query(page_type: str, year: Union[int, None] = None,
                         inventory_num: Union[int, None] = None,
                         size: int = 10000) -> dict:
    match_fields = [{'match': {'metadata.page_type': page_type}}]
    if inventory_num:
        match_fields += [{'match': {'metadata.inventory_num': inventory_num}}]
    if year:
        match_fields += [{'match': {'metadata.year': year}}]
    return make_bool_query(match_fields, size)


def retrieve_inventory_metadata(es: Elasticsearch, inventory_num: int, config):
    if not es.exists(index=config['inventory_index'], doc_type=config['inventory_doc_type'], id=inventory_num):
        raise ValueError('No inventory metadata available for inventory num {}'.format(inventory_num))
    response = es.get(index=config['inventory_index'], doc_type=config['inventory_doc_type'], id=inventory_num)
    return response['_source']


def retrieve_inventory_hocr_scans(es: Elasticsearch, inventory_num: int, config: dict) -> list:
    query = {'query': {'match': {'metadata.inventory_num': inventory_num}}, 'size': 10000}
    response = es.search(index=config['scan_index'], body=query)
    if response['hits']['total'] == 0:
        return []
    return [parse_es_scan_doc(hit['_source']) for hit in response['hits']['hits']]


def retrieve_inventory_scans(es: Elasticsearch, inventory_num: int, config: dict) -> list:
    query = {'query': {'match': {'metadata.inventory_num': inventory_num}}, 'size': 10000}
    return retrieve_scans_by_query(es, query, config)


def retrieve_inventory_pages(es: Elasticsearch, inventory_num: int, config: dict) -> list:
    query = {'query': {'match': {'metadata.inventory_num': inventory_num}}, 'size': 10000}
    return retrieve_pages_by_query(es, query, config)


def retrieve_scan_by_id(es: Elasticsearch, scan_id: str, config) -> Union[dict, None]:
    if not es.exists(index=config['scan_index'], doc_type=config['scan_doc_type'], id=scan_id):
        return None
    response = es.get(index=config['scan_index'], doc_type=config['scan_doc_type'], id=scan_id)
    if '_source' in response:
        scan_doc = parse_es_scan_doc(response['_source'])
        return scan_doc
    else:
        return None


def retrieve_scans_by_query(es: Elasticsearch, query: dict, config) -> List[dict]:
    response = es.search(index=config['scan_index'], body=query)
    if response['hits']['total']['value'] == 0:
        return []
    else:
        return [hit['_source'] for hit in response['hits']['hits']]


def retrieve_page_by_id(es: Elasticsearch, page_id: str, config) -> Union[ResolutionPageDoc, None]:
    if not es.exists(index=config['page_index'], doc_type=config['page_doc_type'], id=page_id):
        return None
    response = es.get(index=config['page_index'], doc_type=config['page_doc_type'], id=page_id)
    if '_source' in response:
        page_doc = page_json_to_resolution_page(response['_source'])
        return page_doc
    else:
        return None


def retrieve_pages_by_query(es: Elasticsearch,
                            query: dict, config: dict,
                            use_scroll: bool = False) -> List[ResolutionPageDoc]:
    hits = []
    if use_scroll:
        for hit in scroll_hits(es, query, config['page_index'], config['page_doc_type'], size=10):
            hits += [hit]
            if len(hits) % 100 == 0:
                print(len(hits), 'hits scrolled')
    else:
        response = es.search(index=config['page_index'], body=query)
        if response['hits']['total'] == 0:
            return []
        hits = response['hits']['hits']
    return parse_hits_as_pages(hits)


def retrieve_page_by_page_number(es: Elasticsearch, page_num: int,
                                 config: dict) -> Union[ResolutionPageDoc, None]:
    match_fields = [{'match': {'metadata.page_num': page_num}}]
    if 'inventory_num' in config:
        match_fields += [{'match': {'metadata.inventory_num': config['inventory_num']}}]
    elif 'year' in config:
        match_fields += [{'match': {'metadata.year': config['year']}}]
    query = make_bool_query(match_fields)
    pages = retrieve_pages_by_query(es, query, config)
    if len(pages) == 0:
        return None
    else:
        return pages[0]


def retrieve_pages_by_page_number_range(es: Elasticsearch, page_num_start: int,
                                        page_num_end: int, config: dict,
                                        use_scroll: bool = False) -> Union[List[ResolutionPageDoc], None]:
    """Retrieve a range of Republic PageXML pages based on page number"""
    match_fields = [{'range': {'metadata.page_num': {'gte': page_num_start, 'lte': page_num_end}}}]
    if 'inventory_num' in config:
        match_fields += [{'match': {'metadata.inventory_num': config['inventory_num']}}]
    elif 'year' in config:
        match_fields += [{'match': {'year': config['year']}}]
    query = make_bool_query(match_fields)
    pages = retrieve_pages_by_query(es, query, config, use_scroll=use_scroll)
    if len(pages) == 0:
        return None
    else:
        return sorted(pages, key=lambda x: x.metadata['page_num'])


def retrieve_pages_by_type(es: Elasticsearch, page_type: str, inventory_num: int,
                           config: dict) -> List[ResolutionPageDoc]:
    query = make_page_type_query(page_type, inventory_num=inventory_num)
    return retrieve_pages_by_query(es, query, config)


def retrieve_pages_by_number_of_columns(es: Elasticsearch, num_columns_min: int,
                                        num_columns_max: int, inventory_config: dict) -> list:
    query = make_column_query(num_columns_min, num_columns_max, inventory_config['inventory_num'])
    return retrieve_pages_by_query(es, query, inventory_config)


def retrieve_title_pages(es: Elasticsearch, inventory_num: int, config: dict) -> list:
    return retrieve_pages_by_type(es, 'title_page', inventory_num, config)


def retrieve_index_pages(es: Elasticsearch, inventory_num: int, config: dict) -> list:
    pages = retrieve_pages_by_type(es, 'index_page', inventory_num, config)
    return sorted(pages, key=lambda page: page.metadata['page_num'])


def retrieve_resolution_pages(es: Elasticsearch, inventory_num: int, config: dict) -> list:
    pages = retrieve_pages_by_type(es, 'resolution_page', inventory_num, config)
    return sorted(pages, key=lambda page: page.metadata['page_num'])


def retrieve_pagexml_resolution_pages(es: Elasticsearch, inv_num: int,
                                      inv_config: dict, use_scroll=False) -> Union[None, List[dict]]:
    try:
        resolution_start, resolution_end = get_pagexml_resolution_page_range(es, inv_num, inv_config)
    except TypeError:
        return None
    return retrieve_pages_by_page_number_range(es, resolution_start, resolution_end, inv_config, use_scroll=use_scroll)


def retrieve_respect_pages(es: Elasticsearch, inventory_num: int, config: dict) -> list:
    return retrieve_pages_by_type(es, 'respect_page', inventory_num, config)


def retrieve_paragraph_by_type_page_number(es: Elasticsearch, page_number: int, config: dict) -> list:
    match_fields = [
        {'match': {'metadata.type_page_num': page_number}},
        {'match': {'metadata.inventory_year': config['year']}}
    ]
    query = make_bool_query(match_fields)
    response = es.search(index=config['paragraph_index'], doc_type=config['paragraph_doc_type'], body=query)
    if response['hits']['total'] == 0:
        return []
    else:
        return [hit['_source'] for hit in response['hits']['hits']]


def retrieve_paragraphs_by_inventory(es: Elasticsearch, inventory_num: int, config: dict) -> list:
    match_fields = [
        {'match': {'metadata.inventory_num': inventory_num}}
    ]
    query = make_bool_query(match_fields)
    response = es.search(index=config['paragraph_index'], doc_type=config['paragraph_doc_type'], body=query)
    if response['hits']['total'] == 0:
        return []
    else:
        return [hit['_source'] for hit in response['hits']['hits']]


def retrieve_pagexml_meetings(es: Elasticsearch, inv_num: int, config: dict) -> List[dict]:
    query = {
        "query": {
            "match": {
                "inventory_num": inv_num
            }
        },
        "size": 1000
    }
    response = es.search(index=config['meeting_index'], doc_type=config['meeting_doc_type'], body=query)
    if response['hits']['total']['value'] == 0:
        return []
    else:
        return [hit['_source'] for hit in response['hits']['hits']]


def retrieve_meetings_by_query(es: Elasticsearch, query: dict, config: dict) -> List[Meeting]:
    response = es.search(index=config['meeting_index'], body=query)
    if response['hits']['total']['value'] == 0:
        return []
    else:
        docs = [hit['_source'] for hit in response['hits']['hits']]
        return [meeting_from_json(doc) for doc in docs]


def retrieve_meeting_by_date(es: Elasticsearch, date: Union[str, RepublicDate], config: dict) -> Union[None, Meeting]:
    if isinstance(date, RepublicDate):
        doc_id = f'meeting-{date.isoformat()}-session-1'
    else:
        doc_id = f'meeting-{date}-session-1'
    if es.exists(index=config["meeting_index"], doc_type=config["meeting_doc_type"], id=doc_id):
        response = es.get(index=config["meeting_index"], doc_type=config["meeting_doc_type"], id=doc_id)
        return meeting_from_json(response['_source'])
    else:
        return None


def retrieve_resolution_by_id(es: Elasticsearch, resolution_id: str, config: dict) -> Union[Resolution, None]:
    if es.exists(index=config['resolution_index'], id=resolution_id):
        response = es.get(index=config['resolution_index'], id=resolution_id)
        return resolution_from_json(response['_source'])
    else:
        return None


def scroll_resolutions_by_query(es: Elasticsearch, query: dict,
                                config: dict, scroll: str = '1m') -> Generator[Resolution, None, None]:
    for hit in scroll_hits(es, query, index=config['resolution_index'],
                           doc_type="_doc", size=10, scroll=scroll):
        resolution_json = hit['_source']
        yield resolution_from_json(resolution_json)


def retrieve_resolutions_by_query(es: Elasticsearch, query: dict,
                                  config: dict) -> List[Resolution]:
    response = es.search(index=config['resolution_index'], doc_type="_doc", body=query)
    if response['hits']['total']['value'] == 0:
        return []
    else:
        return [resolution_from_json(hit['_source']) for hit in response['hits']['hits']]


def scroll_inventory_resolutions(es: Elasticsearch, inv_config: dict):
    query = {'query': {'match': {'metadata.inventory_num': inv_config['inventory_num']}}}
    for resolution in scroll_resolutions_by_query(es, query, inv_config, scroll='20m'):
        yield resolution


def scroll_phrase_matches_by_query(es: Elasticsearch, query: dict,
                                   config: dict, size: int = 100,
                                   scroll: str = '1m') -> Generator[PhraseMatch, None, None]:
    for hit in scroll_hits(es, query, index=config['phrase_match_index'],
                           doc_type="_doc", size=size, scroll=scroll):
        match_json = hit['_source']
        yield parse_phrase_matches([match_json])[0]


def retrieve_phrase_matches_by_query(es: Elasticsearch, query: dict,
                                     config: dict) -> List[PhraseMatch]:
    response = es.search(index=config['phrase_match_index'], doc_type="_doc", body=query)
    if response['hits']['total']['value'] == 0:
        return []
    else:
        return parse_phrase_matches([hit['_source'] for hit in response['hits']['hits']])


def retrieve_phrase_matches_by_paragraph_id(es: Elasticsearch, paragraph_id: str,
                                            config: dict) -> List[PhraseMatch]:
    query = {'query': {'match': {'text_id.keyword': paragraph_id}}, 'size': 1000}
    phrase_matches = retrieve_phrase_matches_by_query(es, query, config)
    # sort matches by order of occurrence in the text
    return sorted(phrase_matches, key=lambda x: x.offset)


def parse_latest_version(es, text_repo, scan_num, inventory_metadata, inventory_config, ignore_version: bool = False):
    doc_id = get_scan_id(inventory_metadata, scan_num)
    import time
    try:
        version_info = text_repo.get_last_version_info(doc_id, file_type=inventory_config['ocr_type'])
        if not version_info:
            return None
        if not ignore_version and es.exists(index=inventory_config["scan_index"], id=doc_id):
            response = es.get(index=inventory_config["scan_index"], id=doc_id)
            indexed_scan = response["_source"]
            if indexed_scan["version"]["id"] == version_info["id"]:
                # this version is already indexed
                return None
        pagexml = text_repo.get_last_version_content(doc_id, inventory_config['ocr_type'])
        file_extension = '.hocr' if inventory_config['ocr_type'] == 'hocr' else '.page.xml'
        scan_doc = pagexml_parser.get_scan_pagexml(doc_id + file_extension, inventory_config, pagexml_data=pagexml)
        scan_doc["version"] = version_info
        return scan_doc
    except ValueError:
        print('missing scan:', doc_id)
        return None


def get_pagexml_resolution_page_range(es: Elasticsearch, inv_num: int, inv_config: dict) -> Union[None, tuple]:
    inv_metadata = retrieve_inventory_metadata(es, inv_num, inv_config)
    try:
        offsets = [offset['page_num_offset'] for offset in inv_metadata['type_page_num_offsets']]
        resolution_start = 0
        for offset in inv_metadata['type_page_num_offsets']:
            if offset['page_type'] == 'resolution_page':
                resolution_start = offset['page_num_offset']
        if resolution_start != offsets[-1]:
            next_section_offset = offsets[offsets.index(resolution_start) + 1]
            resolution_end = next_section_offset - 1
        else:
            resolution_end = inv_metadata['num_pages'] - 1
        return resolution_start, resolution_end
    except IndexError:
        return None


def retrieve_date_num_sessions(es, meeting_date, config):
    query = {'query': {'match': {'metadata.meeting_date': str(meeting_date)}}, 'size': 0}
    response = es.search(index=config['meeting_index'], body=query)
    return response['hits']['total']['value']


def retrieve_meeting_resolutions(es, meeting_date, config):
    query = {'query': {'match': {'metadata.meeting_date': str(meeting_date)}}, 'size': 1000}
    resolutions = retrieve_resolutions_by_query(es, query, config)
    session_resolutions = defaultdict(list)
    for resolution in resolutions:
        session_id = resolution.metadata['id'].split('-resolution-')[0]
        session_resolutions[session_id].append(resolution)
    return session_resolutions


def retrieve_session_resolutions(es, session_id, config):
    query = {'query': {'match': {'metadata.session_id.keyword': session_id}}, 'size': 1000}
    return retrieve_resolutions_by_query(es, query, config)


def retrieve_meeting_phrase_matches(es, meeting_resolutions, config):
    paragraph_ids = [paragraph.metadata['id'] for resolution in meeting_resolutions
                     for paragraph in resolution.paragraphs]
    phrase_matches = []
    for para_id in paragraph_ids:
        query = {'query': {'match': {'text_id.keyword': para_id}}, 'size': 1000}
        phrase_matches += retrieve_phrase_matches_by_query(es, query, config)
    return phrase_matches
