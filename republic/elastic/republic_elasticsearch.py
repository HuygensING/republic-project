import datetime
from typing import Union, List, Dict
from elasticsearch import Elasticsearch, RequestError
import json
import numpy as np
import copy

from republic.config.republic_config import set_config_inventory_num
from republic.fuzzy.fuzzy_context_searcher import FuzzyContextSearcher
from republic.model.republic_hocr_model import HOCRPage
from republic.model.republic_phrase_model import category_index
from republic.model.republic_meeting import Meeting, meeting_from_json
from republic.model.republic_date import RepublicDate
from republic.model.republic_pagexml_model import parse_derived_coords
import republic.parser.republic_file_parser as file_parser
import republic.parser.republic_inventory_parser as inv_parser
import republic.parser.hocr.republic_base_page_parser as hocr_base_parser
import republic.parser.hocr.republic_page_parser as hocr_page_parser
import republic.parser.hocr.republic_paragraph_parser as hocr_para_parser
import republic.parser.pagexml.republic_pagexml_parser as pagexml_parser
import republic.parser.pagexml.pagexml_meeting_parser as meeting_parser
from settings import text_repo_url
from republic.download.text_repo import TextRepo
from settings import set_elasticsearch_config


def initialize_es(host_type: str = 'internal', timeout: int = 10) -> Elasticsearch:
    republic_config = set_elasticsearch_config(host_type)
    es_config = republic_config['elastic_config']
    if es_config['url_prefix']:
        es_republic = Elasticsearch([{'host': es_config['host'],
                                      'port': es_config['port'],
                                      'scheme': es_config['scheme'],
                                      'url_prefix': es_config['url_prefix']}],
                                    timeout=timeout)
    else:
        es_republic = Elasticsearch([{'host': es_config['host'],
                                      'port': es_config['port'],
                                      'scheme': es_config['scheme']}],
                                    timeout=timeout)
    return es_republic


def scroll_hits(es: Elasticsearch, query: dict, index: str, doc_type: str, size: int = 100) -> iter:
    response = es.search(index=index, doc_type=doc_type, scroll='2m', size=size, body=query)
    sid = response['_scroll_id']
    scroll_size = response['hits']['total']
    print('total hits:', scroll_size)
    if type(scroll_size) == dict:
        scroll_size = scroll_size['value']
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


def parse_hits_as_pages(hits: dict) -> List[dict]:
    return [parse_es_page_doc(hit['_source']) for hit in hits]


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


def retrieve_inventory_pages(es: Elasticsearch, inventory_num: int, config: dict) -> list:
    query = {'query': {'match': {'metadata.inventory_num': inventory_num}}, 'size': 10000}
    return retrieve_pages_with_query(es, query, config)


def retrieve_page_doc(es: Elasticsearch, page_id: str, config) -> Union[dict, None]:
    if not es.exists(index=config['page_index'], doc_type=config['page_doc_type'], id=page_id):
        return None
    response = es.get(index=config['page_index'], doc_type=config['page_doc_type'], id=page_id)
    if '_source' in response:
        page_doc = parse_es_page_doc(response['_source'])
        return page_doc
    else:
        return None


def retrieve_pages_with_query(es: Elasticsearch,
                              query: dict, config: dict,
                              use_scroll: bool = False) -> List[Dict[str, Union[str, int, List, Dict]]]:
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


def retrieve_page_by_page_number(es: Elasticsearch, page_num: int, config: dict) -> Union[dict, None]:
    match_fields = [{'match': {'metadata.page_num': page_num}}]
    if 'inventory_num' in config:
        match_fields += [{'match': {'metadata.inventory_num': config['inventory_num']}}]
    elif 'year' in config:
        match_fields += [{'match': {'metadata.year': config['year']}}]
    query = make_bool_query(match_fields)
    print(query)
    pages = retrieve_pages_with_query(es, query, config)
    if len(pages) == 0:
        return None
    else:
        return pages[0]


def retrieve_pages_by_page_number_range(es: Elasticsearch, page_num_start: int,
                                        page_num_end: int, config: dict,
                                        use_scroll: bool = False) -> Union[List[dict], None]:
    """Retrieve a range of Republic PageXML pages based on page number"""
    match_fields = [{'range': {'metadata.page_num': {'gte': page_num_start, 'lte': page_num_end}}}]
    if 'inventory_num' in config:
        match_fields += [{'match': {'metadata.inventory_num': config['inventory_num']}}]
    elif 'year' in config:
        match_fields += [{'match': {'year': config['year']}}]
    query = make_bool_query(match_fields)
    pages = retrieve_pages_with_query(es, query, config, use_scroll=use_scroll)
    if len(pages) == 0:
        return None
    else:
        return sorted(pages, key=lambda x: x['metadata']['page_num'])


def retrieve_pages_by_type(es: Elasticsearch, page_type: str, inventory_num: int, config: dict) -> List[dict]:
    query = make_page_type_query(page_type, inventory_num=inventory_num)
    return retrieve_pages_with_query(es, query, config)


def retrieve_pages_by_number_of_columns(es: Elasticsearch, num_columns_min: int,
                                        num_columns_max: int, inventory_config: dict) -> list:
    query = make_column_query(num_columns_min, num_columns_max, inventory_config['inventory_num'])
    return retrieve_pages_with_query(es, query, inventory_config)


def retrieve_title_pages(es: Elasticsearch, inventory_num: int, config: dict) -> list:
    return retrieve_pages_by_type(es, 'title_page', inventory_num, config)


def retrieve_index_pages(es: Elasticsearch, inventory_num: int, config: dict) -> list:
    return retrieve_pages_by_type(es, 'index_page', inventory_num, config)


def retrieve_resolution_pages(es: Elasticsearch, inventory_num: int, config: dict) -> list:
    return retrieve_pages_by_type(es, 'resolution_page', inventory_num, config)


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


def get_meeting_by_date(es: Elasticsearch, date: Union[str, RepublicDate], config: dict) -> Union[None, Meeting]:
    if isinstance(date, RepublicDate):
        doc_id = f'meeting-{date.isoformat()}-session-1'
    else:
        doc_id = f'meeting-{date}-session-1'
    if es.exists(index=config["meeting_index"], doc_type=config["meeting_doc_type"], id=doc_id):
        response = es.get(index=config["meeting_index"], doc_type=config["meeting_doc_type"], id=doc_id)
        return meeting_from_json(response['_source'])
    else:
        return None


def correct_section_types(inv_metadata):
    section_starts = {offsets['page_num_offset']: offsets['page_type'] for offsets in
                      inv_metadata['type_page_num_offsets']}
    for section in inv_metadata['sections']:
        if section['start'] in section_starts:
            section['page_type'] = section_starts[section['start']]
    return None


def get_per_page_type_index(inv_metadata):
    page_type = {page_num: 'empty_page' for page_num in np.arange(inv_metadata['num_pages'])}
    for page_num in inv_metadata['title_page_nums']:
        page_type[page_num] = 'title_page'
    for section in inv_metadata['sections']:
        for page_num in np.arange(section['start'], section['end'] + 1):
            page_type[page_num] = section['page_type']
            if page_num in inv_metadata['title_page_nums']:
                page_type[page_num] = [section['page_type'], 'title_page']
    return page_type


def add_pagexml_page_types(es, inv_config):
    inv_metadata = retrieve_inventory_metadata(es, inv_config["inventory_num"], inv_config)
    page_type_index = get_per_page_type_index(inv_metadata)
    pages = retrieve_inventory_pages(es, inv_config["inventory_num"], inv_config)
    for pi, page in enumerate(sorted(pages, key=lambda x: x['metadata']['page_num'])):
        if page["metadata"]["page_num"] not in page_type_index:
            page['metadata']['page_type'] = "empty_page"
        else:
            page['metadata']['page_type'] = page_type_index[page['metadata']['page_num']]
        es.index(index=inv_config["page_index"], id=page['metadata']['id'], body=page)
        print(page['metadata']['id'], page["metadata"]["page_type"])


def delete_es_index(es: Elasticsearch, index: str):
    if es.indices.exists(index=index):
        print('exists, deleting')
        es.indices.delete(index=index)


def index_inventory_metadata(es: Elasticsearch, inventory_metadata: dict, config: dict):
    inventory_metadata['index_timestamp'] = datetime.datetime.now()
    es.index(index=config['inventory_index'], doc_type=config['inventory_doc_type'],
             id=inventory_metadata['inventory_num'], body=inventory_metadata)


def index_scan(es: Elasticsearch, scan_hocr: dict, config: dict):
    doc = create_es_scan_doc(scan_hocr)
    doc['metadata']['index_timestamp'] = datetime.datetime.now()
    es.index(index=config['scan_index'], doc_type=config['scan_doc_type'],
             id=scan_hocr['metadata']['id'], body=doc)


def index_page(es: Elasticsearch, page_hocr: dict, config: dict):
    doc = create_es_page_doc(page_hocr)
    doc['metadata']['index_timestamp'] = datetime.datetime.now()
    es.index(index=config['page_index'], doc_type=config['page_doc_type'],
             id=page_hocr['metadata']['id'], body=doc)


def index_lemmata(es: Elasticsearch, lemma_index: dict, config: dict):
    for lemma in lemma_index:
        lemma_doc = create_es_index_lemma_doc(lemma, lemma_index, config)
        doc_id = f'{config["inventory_num"]}---{normalize_lemma(lemma)}'
        try:
            es.index(index=config['lemma_index'], doc_type=config['lemma_doc_type'], id=doc_id, body=lemma_doc)
        except RequestError:
            print(f'Error indexing lemma term with id {doc_id}')
            raise


def normalize_lemma(lemma):
    lemma = lemma.replace(' ', '_').replace('/', '_').replace('ê', 'e')
    return lemma


def index_inventory_from_zip(es: Elasticsearch, inventory_num: int, inventory_config: dict):
    for scan_doc in inv_parser.parse_inventory_from_zip(inventory_num, inventory_config):
        if not scan_doc:
            continue
        index_scan(es, scan_doc, inventory_config)
        if 'double_page' not in scan_doc['metadata']['scan_type']:
            continue
        if inventory_config['ocr_type'] == 'hocr':
            pages_doc = hocr_page_parser.parse_double_page_scan(scan_doc, inventory_config)
        else:
            pages_doc = pagexml_parser.split_pagexml_scan(scan_doc)
        for page_doc in pages_doc:
            index_page(es, page_doc, inventory_config)


def parse_latest_version(es, text_repo, scan_num, inventory_metadata, inventory_config, ignore_version: bool = False):
    doc_id = get_scan_id(inventory_metadata, scan_num)
    try:
        version_info = text_repo.get_last_version_info(doc_id, file_type=inventory_config['ocr_type'])
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


def get_scan_id(inventory_metadata, scan_num):
    scan_num_str = (4 - len(str(scan_num))) * "0" + str(scan_num)
    return f'{inventory_metadata["series_name"]}_{inventory_metadata["inventory_num"]}_{scan_num_str}'


def index_inventory_from_text_repo(es, inv_num, inventory_config: Dict[str, any], ignore_version: bool = False):
    text_repo = TextRepo(text_repo_url)
    inventory_metadata = retrieve_inventory_metadata(es, inv_num, inventory_config)
    if "num_scans" not in inventory_metadata:
        return None
    for scan_num in range(1, inventory_metadata["num_scans"]+1):
        scan_doc = parse_latest_version(es, text_repo, scan_num, inventory_metadata,
                                        inventory_config, ignore_version=ignore_version)
        if not scan_doc:
            continue
        print("Indexing scan", scan_doc["metadata"]["id"])
        index_scan(es, scan_doc, inventory_config)
        if 'double_page' not in scan_doc['metadata']['scan_type']:
            continue
        if inventory_config['ocr_type'] == 'hocr':
            pages_doc = hocr_page_parser.parse_double_page_scan(scan_doc, inventory_config)
        else:
            pages_doc = pagexml_parser.split_pagexml_scan(scan_doc)
        for page_doc in pages_doc:
            page_doc["version"] = scan_doc["version"]
            index_page(es, page_doc, inventory_config)


def index_hocr_inventory(es: Elasticsearch, inventory_num: int, base_config: dict, base_dir: str):
    inventory_config = set_config_inventory_num(base_config, inventory_num, base_dir, ocr_type="hocr")
    # print(inventory_config)
    scan_files = file_parser.get_hocr_files(inventory_config['hocr_dir'])
    for scan_file in scan_files:
        scan_hocr = hocr_page_parser.get_scan_hocr(scan_file, config=inventory_config)
        if not scan_hocr:
            continue
        if 'double_page' in scan_hocr['metadata']['scan_type']:
            # print('double page scan:', scan_hocr['scan_num'], scan_hocr['scan_type'])
            pages_hocr = hocr_page_parser.parse_double_page_scan(scan_hocr, inventory_config)
            for page_hocr in pages_hocr:
                # print(inventory_num, page_hocr['page_num'], page_hocr['page_type'])
                index_page(es, page_hocr, inventory_config)
        else:
            # print('NOT DOUBLE PAGE:', scan_hocr['scan_num'], scan_hocr['scan_type'])
            index_scan(es, scan_hocr, inventory_config)
            continue


def index_pre_split_column_inventory(es: Elasticsearch, pages_info: dict, config: dict, delete_index: bool = False):
    numbering = 0
    if delete_index:
        delete_es_index(es, config['page_index'])
    for doc_id in pages_info:
        numbering += 1
        page_doc = hocr_page_parser.make_page_doc(doc_id, pages_info, config)
        page_doc['num_columns'] = len(page_doc['columns'])
        try:
            page_type = hocr_page_parser.get_page_type(page_doc, config, debug=False)
        except TypeError:
            print(json.dumps(page_doc, indent=2))
            raise
        page_doc['page_type'] = page_type
        page_doc['is_parseable'] = True if page_type != 'bad_page' else False
        if hocr_base_parser.is_title_page(page_doc, config['title_page']):
            # reset numbering
            numbering = 1
            # page_doc['page_type'] += ['title_page']
            page_doc['is_title_page'] = True
        else:
            page_doc['is_title_page'] = False
        page_doc['type_page_num'] = numbering
        page_doc['type_page_num_checked'] = False
        ##################################
        # DIRTY HACK FOR INVENTORY 3780! #
        if page_doc['page_num'] in [89, 563, 565]:
            if 'title_page' not in page_doc['page_type']:
                page_doc['page_type'] += ['title_page']
            page_doc['is_title_page'] = True
        ##################################
        page_es_doc = create_es_page_doc(page_doc)
        print(config['inventory_num'], page_doc['page_num'], page_doc['page_type'])
        page_doc['metadata']['index_timestamp'] = datetime.datetime.now()
        es.index(index=config['page_index'], doc_type=config['page_doc_type'], id=doc_id, body=page_es_doc)
        # print(doc_id, page_type, numbering)


def index_inventory_hocr_scans(es: Elasticsearch, config: dict):
    scan_files = file_parser.get_hocr_files(config['hocr_dir'])
    for scan_file in scan_files:
        scan_hocr = hocr_page_parser.get_scan_hocr(scan_file, config=config)
        if not scan_hocr:
            continue
        print("Indexing scan", scan_hocr["id"])
        scan_es_doc = create_es_scan_doc(scan_hocr)
        scan_es_doc['metadata']['index_timestamp'] = datetime.datetime.now()
        es.index(index=config['scan_index'], doc_type=config['scan_doc_type'],
                 id=scan_es_doc['id'], body=scan_es_doc)


def index_inventory_hocr_pages(es: Elasticsearch, inventory_num: int, config: dict):
    scans_hocr: list = retrieve_inventory_hocr_scans(es, inventory_num, config)
    print('number of scans:', len(scans_hocr))
    for scan_hocr in scans_hocr:
        if 'double_page' in scan_hocr['scan_type']:
            pages_hocr = hocr_page_parser.parse_double_page_scan(scan_hocr, config)
            for page_hocr in pages_hocr:
                print('Indexing page', page_hocr['id'])
                index_page(es, page_hocr, config)
        elif 'small' in scan_hocr['scan_type']:
            scan_hocr['page_type'] = ['empty_page', 'book_cover']
            scan_hocr['columns'] = []
            if scan_hocr['scan_num'] == 1:
                scan_hocr['id'] = '{}-page-1'.format(scan_hocr['scan_num'])
            else:
                scan_hocr['id'] = '{}-page-{}'.format(scan_hocr['scan_num'], scan_hocr['scan_num'] * 2 - 2)
            index_page(es, scan_hocr, config)
        else:
            print('Non-double page:', scan_hocr['scan_num'], scan_hocr['scan_type'])


def index_paragraphs(es: Elasticsearch, fuzzy_searcher: FuzzyContextSearcher,
                     inventory_num: int, inventory_config: dict):
    current_date = hocr_para_parser.initialize_current_date(inventory_config)
    page_docs = retrieve_resolution_pages(es, inventory_num, inventory_config)
    print('Pages retrieved:', len(page_docs), '\n')
    for page_doc in sorted(page_docs, key=lambda x: x['page_num']):
        if 'resolution_page' not in page_doc['page_type']:
            continue
        try:
            hocr_page = HOCRPage(page_doc, inventory_config)
        except KeyError:
            print('Error parsing page', page_doc['id'])
            continue
            # print(json.dumps(page_doc, indent=2))
            # raise
        paragraphs, header = hocr_para_parser.get_resolution_page_paragraphs(hocr_page, inventory_config)
        for paragraph_order, paragraph in enumerate(paragraphs):
            matches = fuzzy_searcher.find_candidates(paragraph['text'], include_variants=True)
            if hocr_para_parser.matches_resolution_phrase(matches):
                paragraph['metadata']['type'] = 'resolution'
            current_date = hocr_para_parser.track_meeting_date(paragraph, matches, current_date, inventory_config)
            paragraph['metadata']['keyword_matches'] = matches
            for match in matches:
                if match['match_keyword'] in category_index:
                    category = category_index[match['match_keyword']]
                    match['match_category'] = category
                    paragraph['metadata']['categories'].add(category)
            paragraph['metadata']['categories'] = list(paragraph['metadata']['categories'])
            del paragraph['lines']
            paragraph['metadata']['index_timestamp'] = datetime.datetime.now()
            es.index(index=inventory_config['paragraph_index'], doc_type=inventory_config['paragraph_doc_type'],
                     id=paragraph['metadata']['paragraph_id'], body=paragraph)


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


def index_meetings_inventory(es: Elasticsearch, inv_num: int, inv_config: dict) -> None:
    pages = retrieve_pagexml_resolution_pages(es, inv_num, inv_config)
    inv_metadata = retrieve_inventory_metadata(es, inv_num, inv_config)
    prev_date: Union[None, RepublicDate] = None
    if not pages:
        print('No pages retrieved for inventory', inv_num)
        return None
    for mi, meeting in enumerate(meeting_parser.get_meeting_dates(pages, inv_num, inv_metadata)):
        if meeting.metadata['num_lines'] > 4000:
            # exceptionally long meeting docs probably contain multiple meetings
            # so quarantine these
            meeting.metadata['date_shift_status'] = 'quarantined'
            # print('Error: too many lines for meeting on date', meeting.metadata['meeting_date'])
            # continue
        meeting_date_string = 'None'
        for missing_meeting in add_missing_dates(prev_date, meeting):
            missing_meeting.metadata['index_timestamp'] = datetime.datetime.now()
            es.index(index=inv_config['meeting_index'], doc_type=inv_config['meeting_doc_type'],
                     id=missing_meeting.id, body=missing_meeting.to_json(with_columns=True, with_page_versions=True))

        meeting.page_versions = meeting_parser.get_meeting_pages_version(meeting)
        meeting.clean_lines()
        if meeting.metadata['has_meeting_date_element']:
            for evidence in meeting.metadata['evidence']:
                if evidence['metadata_field'] == 'meeting_date':
                    meeting_date_string = evidence['matches'][-1]['match_string']
        page_num = int(meeting.columns[0]['metadata']['column_id'].split('page-')[1].split('-')[0])
        num_lines = meeting.metadata['num_lines']
        meeting_id = meeting.metadata['id']
        print(
            f"{mi}\t{meeting_id}\t{meeting_date_string: <30}\tnum_lines: {num_lines}\tpage: {page_num}")

        #print('Indexing meeting on date', meeting.metadata['meeting_date'],
        #      '\tdate_string:', meeting_date_string,
        #      '\tnum meeting lines:', meeting.metadata['num_lines'])
        prev_date = meeting.date
        try:
            meeting.metadata['index_timestamp'] = datetime.datetime.now()
            if meeting.metadata['date_shift_status'] == 'quarantined':
                quarantine_index = inv_config['meeting_index'] + '_quarantine'
                es.index(index=quarantine_index, doc_type=inv_config['meeting_doc_type'],
                         id=meeting.id, body=meeting.to_json(with_columns=True, with_page_versions=True))
            else:
                es.index(index=inv_config['meeting_index'], doc_type=inv_config['meeting_doc_type'],
                         id=meeting.id, body=meeting.to_json(with_columns=True, with_page_versions=True))
        except RequestError:
            print('skipping doc')
            continue
    return None


def add_missing_dates(prev_date: Union[RepublicDate, None], meeting: Meeting):
    if prev_date is None:
        prev_date = RepublicDate(meeting.date.year - 1, 12, 31)
        print("prev_date:", prev_date.isoformat(), "\tcurr_date:", meeting.date.isoformat())
    missing = (meeting.date - prev_date).days - 1
    if missing > 0:
        print("missing days:", missing)
    for diff in range(1, missing+1):
        # create a new meeting doc for the missing date, with data copied from the current meeting
        # as most likely the missing date is a non-meeting date with 'nihil actum est'
        missing_date = prev_date.date + datetime.timedelta(days=diff)
        missing_date = RepublicDate(missing_date.year, missing_date.month, missing_date.day)
        missing_meeting = copy.deepcopy(meeting)
        missing_meeting.metadata["id"] = f"meeting-{missing_date.isoformat()}-session-1"
        missing_meeting.id = missing_meeting.metadata["id"]
        missing_meeting.metadata["meeting_date"] = missing_date.isoformat()
        missing_meeting.metadata["year"] = missing_date.year
        missing_meeting.metadata["meeting_month"] = missing_date.month
        missing_meeting.metadata["meeting_day"] = missing_date.day
        missing_meeting.metadata["meeting_weekday"] = missing_date.day_name
        missing_meeting.metadata["is_workday"] = missing_date.is_work_day()
        missing_meeting.metadata["session"] = None
        missing_meeting.metadata["president"] = None
        missing_meeting.metadata["attendants_list_id"] = None
        evidence_lines = set([evidence["line_id"] for evidence in missing_meeting.metadata["evidence"]])
        keep_columns = []
        num_lines = 0
        missing_meeting.lines = []
        for column in missing_meeting.columns:
            keep_textregions = []
            for textregion in column["textregions"]:
                keep_lines = []
                for line in textregion["lines"]:
                    if len(evidence_lines) > 0:
                        keep_lines += [line]
                        missing_meeting.lines += [line]
                        num_lines += 1
                    else:
                        break
                    if line["id"] in evidence_lines:
                        evidence_lines.remove(line["id"])
                textregion["lines"] = keep_lines
                if len(textregion["lines"]) > 0:
                    textregion["coords"] = parse_derived_coords(textregion["lines"])
                    keep_textregions += [textregion]
            column["textregions"] = keep_textregions
            if len(column["textregions"]) > 0:
                column["coords"] = parse_derived_coords(column["textregions"])
                keep_columns += [column]
        missing_meeting.columns = keep_columns
        missing_meeting.metadata["num_lines"] = num_lines
        missing_meeting.page_versions = meeting_parser.get_meeting_pages_version(missing_meeting)
        missing_meeting.clean_lines()
        print("missing meeting:", missing_meeting.id)
        yield missing_meeting
