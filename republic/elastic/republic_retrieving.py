from typing import Union, List, Dict, Generator
import re

import elasticsearch
from elasticsearch import Elasticsearch
from fuzzy_search.fuzzy_match import PhraseMatch

from settings import text_repo_url
from republic.download.text_repo import TextRepo
from republic.helper.metadata_helper import get_scan_id
import republic.helper.pagexml_helper as pagexml
from republic.model.republic_date import RepublicDate
import republic.model.republic_document_model as rdm
import republic.model.physical_document_model as pdm
import republic.parser.pagexml.republic_pagexml_parser as pagexml_parser


def get_docs(response: Dict[str, any]) -> List[dict]:
    if response['hits']['total']['value'] == 0:
        return []
    else:
        return [hit['_source'] for hit in response['hits']['hits']]


def extract_hits(hits: Union[Dict[str, any], List[Dict[str, any]]]) -> List[Dict[str, any]]:
    if isinstance(hits, dict) and 'hits' in hits:
        if hits['hits']['total']['value'] == 0:
            return []
        hits = hits['hits']['hits']
    return hits


def parse_hits_as_scans(hits: Union[Dict[str, any], List[Dict[str, any]]]) -> List[pdm.PageXMLScan]:
    return [pagexml.json_to_pagexml_scan(hit['_source']) for hit in extract_hits(hits)]


def parse_hits_as_pages(hits: Union[Dict[str, any], List[Dict[str, any]]]) -> List[pdm.PageXMLPage]:
    return [pagexml.json_to_pagexml_page(hit['_source']) for hit in extract_hits(hits)]


def make_bool_query(match_fields, size: int = 10000) -> dict:
    return {
        'query': {
            'bool': {
                'must': match_fields
            }
        },
        'size': size
    }


def make_paragraph_term_query(term: str) -> Dict[str, any]:
    return {
        'query': {
            'bool': {
                'must': [
                    {'match': {'paragraphs.text': term}},
                    {'match': {'type': 'resolution'}}
                ]
            }
        }
    }


def make_text_repo_inventory_query(inventory_num):
    """Returns a Nested Query to match a key/value pair for inventory numbers in the Text Repository."""
    return {
        "query": {
            "nested": {
                "path": "doc.metadata",
                "query": {
                    "bool": {
                        "must": [
                            {"match": {"doc.metadata.key": "inventaris"}},
                            {"match": {"doc.metadata.value": str(inventory_num)}}
                        ]
                    }
                }
            }
        },
        'size': 2
    }


def make_inventory_query(inventory_num: int, size: int = 10):
    return {
        'query': {
            'match': {
                'metadata.inventory_num': inventory_num
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


def make_text_page_num_query(page_num: str):
    return {
        "query": {
            "bool": {
                "must": {
                    "match": {"metadata.text_page_num": page_num}
                }
            }
        }
    }


def make_page_type_query(page_type: str, year: Union[int, None] = None,
                         inventory_num: Union[int, None] = None,
                         size: int = 10000) -> dict:
    match_fields = [{'match': {'type': page_type}}]
    if inventory_num:
        match_fields += [{'match': {'metadata.inventory_num': inventory_num}}]
    if year:
        match_fields += [{'match': {'metadata.year': year}}]
    return make_bool_query(match_fields, size)


def select_latest_tesseract_version(versions: List[Dict[str, any]]) -> Dict[str, any]:
    return sorted(versions, key=lambda version: version['createdAt'])[-1]


def get_tesseract_versions(doc: Dict[str, any]) -> List[Dict[str, any]]:
    versions = []
    for version in doc['versions']:
        for field in version['metadata']:
            if field['key'] == 'pim:transcription:transcriber' and field['value'] == 'CustomTesseractPageXML':
                versions.append(version)
    return versions


def is_tesseract_version(version: Dict[str, any], text_repo: TextRepo):
    version_metadata = text_repo.get_version_metadata(version['id'])
    return version_metadata['pim:transcription:transcriber'] == 'CustomTesseractPageXML'


def get_tesseract_versions_by_external_id(external_id: str, text_repo: TextRepo):
    versions_info = text_repo.get_file_type_versions(external_id, 'pagexml')
    return [version for version in versions_info['items'] if is_tesseract_version(version, text_repo)]


def select_year_inv(year: int = None, inventory_num: int = None) -> Dict[str, Dict[str, int]]:
    if year is None and inventory_num is None:
        raise ValueError('must use either "year" or "inventory_num"')
    if inventory_num is not None:
        return {'match': {'metadata.inventory_num': inventory_num}}
    elif year is not None:
        return {'match': {'metadata.year': year}}


class Retriever:

    def __init__(self, es_anno: Elasticsearch, es_text: Elasticsearch, config: dict):
        self.es_anno = es_anno
        self.es_text = es_text
        self.config = config

    def scroll_hits(self, es: Elasticsearch, query: dict, index: str, doc_type: str = '_doc',
                    size: int = 100, scroll: str = '2m') -> iter:
        response = es.search(index=index, doc_type=doc_type, scroll=scroll, size=size, body=query)
        sid = response['_scroll_id']
        scroll_size = response['hits']['total']
        print('total hits:', scroll_size, "\thits per scroll:", len(response['hits']['hits']))
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
        try:
            self.es_anno.clear_scroll(scroll_id=sid)
        except elasticsearch.ElasticsearchException:
            print('WARNING: no scroll id found when clearing scroll at end of scroll with query:')
            print(query)
            pass

    def retrieve_inventory_metadata(self, inventory_num: int) -> Dict[str, any]:
        if not self.es_anno.exists(index=self.config['inventory_index'],
                                   doc_type=self.config['inventory_doc_type'],
                                   id=str(inventory_num)):
            raise ValueError('No inventory metadata available for inventory num {}'.format(inventory_num))
        response = self.es_anno.get(index=self.config['inventory_index'],
                                    doc_type=self.config['inventory_doc_type'],
                                    id=str(inventory_num))
        return response['_source']

    def retrieve_inventory_scans(self, inventory_num: int) -> list:
        query = {'query': {'match': {'metadata.inventory_num': inventory_num}}, 'size': 10000}
        return self.retrieve_scans_by_query(query)

    def retrieve_inventory_pages(self, inventory_num: int) -> list:
        query = {'query': {'match': {'metadata.inventory_num': inventory_num}}, 'size': 10000}
        return self.retrieve_pages_by_query(query)

    def retrieve_scan_by_id(self, scan_id: str) -> Union[pdm.PageXMLScan, None]:
        if not self.es_anno.exists(index=self.config['scan_index'], id=scan_id):
            return None
        response = self.es_anno.get(index=self.config['scan_index'], id=scan_id)
        return pagexml.json_to_pagexml_scan(response['_source'])

    def retrieve_scans_by_query(self, query: dict) -> List[pdm.PageXMLScan]:
        for hit in self.scroll_hits(self.es_anno, query, self.config['scan_index'], size=2, scroll='5m'):
            yield pagexml.json_to_pagexml_scan(hit['_source'])
        # response = self.es_anno.search(index=self.config['scan_index'], body=query)
        # return parse_hits_as_scans(response)

    def retrieve_text_repo_scans_by_inventory(self,
                                              inventory_num: int) -> Generator[pdm.PageXMLScan, None, None]:
        text_repo = TextRepo(text_repo_url)
        query = make_text_repo_inventory_query(inventory_num)
        for hi, hit in enumerate(self.scroll_hits(self.es_text, query, index='file', size=2)):
            doc = hit['_source']
            versions = get_tesseract_versions(doc)
            if len(versions) == 0:
                continue
                # raise ValueError(f"Document has no versions: {doc['doc']['externalId']}")
            version = select_latest_tesseract_version(versions)
            scan_pagexml = text_repo.get_content_by_version_id(version['id'])
            filename = f"{doc['doc']['externalId']}.xml"
            scan_doc = pagexml_parser.get_scan_pagexml(filename, pagexml_data=scan_pagexml)
            scan_doc.metadata['textrepo_version'] = version
            yield scan_doc

    def retrieve_page_by_id(self, page_id: str) -> Union[pdm.PageXMLPage, None]:
        if not self.es_anno.exists(index=self.config['page_index'], id=page_id):
            return None
        response = self.es_anno.get(index=self.config['page_index'], id=page_id)
        return pagexml.json_to_pagexml_page(response['_source'])

    def retrieve_pages_by_query(self, query: dict) -> List[pdm.PageXMLPage]:
        hits = []
        for hit in self.scroll_hits(self.es_anno, query, self.config['page_index'], '_doc', size=10):
            hits += [hit]
        return parse_hits_as_pages(hits)

    def retrieve_page_by_page_number(self, page_num: int, year: int = None,
                                     inventory_num: int = None) -> Union[pdm.PageXMLPage, None]:
        match_fields = [
            {'match': {'metadata.page_num': page_num}},
            select_year_inv(year=year, inventory_num=inventory_num)
        ]
        query = make_bool_query(match_fields)
        pages = self.retrieve_pages_by_query(query)
        return None if len(pages) == 0 else pages[0]

    def retrieve_page_by_text_page_number(self, text_page_num: int, year: int = None,
                                          inventory_num: int = None) -> Union[pdm.PageXMLPage, None]:
        match_fields = [
            {'match': {'metadata.text_page_num': text_page_num}},
            select_year_inv(year=year, inventory_num=inventory_num)
        ]
        query = make_bool_query(match_fields)
        pages = self.retrieve_pages_by_query(query)
        return None if len(pages) == 0 else pages[0]

    def retrieve_pages_by_page_number_range(self, page_num_start: int, page_num_end: int, year: int = None,
                                            inventory_num: int = None) -> Union[List[pdm.PageXMLPage], None]:
        """Retrieve a range of Republic PageXML pages based on page number"""
        bool_elements = [
            {'range': {'metadata.page_num': {'gte': page_num_start, 'lte': page_num_end}}},
            select_year_inv(year=year, inventory_num=inventory_num)
        ]
        query = make_bool_query(bool_elements)
        pages = self.retrieve_pages_by_query(query)
        return sorted(pages, key=lambda x: x.metadata['page_num'])

    def retrieve_pages_by_type(self, page_type: str, inventory_num: int) -> List[pdm.PageXMLPage]:
        query = make_page_type_query(page_type, inventory_num=inventory_num)
        return self.retrieve_pages_by_query(query)

    def retrieve_pages_by_number_of_columns(self, num_columns_min: int,
                                            num_columns_max: int, inventory_config: dict) -> list:
        query = make_column_query(num_columns_min, num_columns_max, inventory_config['inventory_num'])
        return self.retrieve_pages_by_query(query)

    def retrieve_title_pages(self, inventory_num: int) -> List[pdm.PageXMLPage]:
        return self.retrieve_pages_by_type('title_page', inventory_num)

    def retrieve_index_pages(self, inventory_num: int) -> List[pdm.PageXMLPage]:
        pages = self.retrieve_pages_by_type('index_page', inventory_num)
        return sorted(pages, key=lambda page: page.metadata['page_num'])

    def retrieve_inventory_resolution_pages(self, inventory_num: int) -> List[pdm.PageXMLPage]:
        pages = self.retrieve_pages_by_type('resolution_page', inventory_num)
        return sorted(pages, key=lambda page: page.metadata['page_num'])

    def retrieve_pagexml_resolution_pages(self, inventory_num: int) -> List[pdm.PageXMLPage]:
        try:
            resolution_start, resolution_end = self.get_pagexml_resolution_page_range(inventory_num)
        except TypeError:
            return []
        return self.retrieve_pages_by_page_number_range(resolution_start, resolution_end)

    def retrieve_respect_pages(self, inventory_num: int) -> List[pdm.PageXMLPage]:
        return self.retrieve_pages_by_type('respect_page', inventory_num)

    def retrieve_paragraph_by_type_page_number(self, page_number: int, year: int = None,
                                               inventory_num: int = None) -> list:
        match_fields = [
            {'match': {'metadata.type_page_num': page_number}},
            {'match': {'metadata.inventory_year': select_year_inv(year, inventory_num)}}
        ]
        query = make_bool_query(match_fields)
        return self.retrieve_paragraph_by_query(query)

    def retrieve_paragraphs_by_inventory(self, inventory_num: int) -> list:
        match_fields = [
            {'match': {'metadata.inventory_num': inventory_num}}
        ]
        query = make_bool_query(match_fields)
        return self.retrieve_paragraph_by_query(query)

    def retrieve_paragraph_by_query(self, query: dict):
        response = self.es_anno.search(index=self.config['paragraph_index'],
                                       doc_type=self.config['paragraph_doc_type'],
                                       body=query)
        return [hit['_source'] for hit in response['hits']['hits']] if 'hits' in response['hits'] else []

    def retrieve_inventory_sessions_with_lines(self, inventory_num: int) -> Generator[rdm.Session, None, None]:
        query = make_inventory_query(inventory_num=inventory_num, size=1000)
        for hit in self.scroll_hits(self.es_anno, query, self.config['session_lines_index'],
                                    size=2, scroll='10m'):
            session = rdm.json_to_republic_session(hit['_source'])
            yield session

    def retrieve_pagexml_sessions(self, inventory_num: int) -> List[dict]:
        query = make_inventory_query(inventory_num, size=1000)
        response = self.es_anno.search(index=self.config['session_index'],
                                       doc_type=self.config['session_doc_type'],
                                       body=query)
        if response['hits']['total']['value'] == 0:
            return []
        else:
            return [hit['_source'] for hit in response['hits']['hits']]

    def retrieve_sessions_by_query(self, query: dict) -> List[rdm.Session]:
        response = self.es_anno.search(index=self.config['session_lines_index'], body=query)
        if response['hits']['total']['value'] == 0:
            return []
        else:
            docs = [hit['_source'] for hit in response['hits']['hits']]
            return [rdm.json_to_republic_session(doc) for doc in docs]

    def retrieve_session_text_by_date(self, date: Union[str, RepublicDate]) -> Union[None, rdm.Session]:
        session_index = 'session_text'
        return self.retrieve_session_by_date(date, session_index)

    def retrieve_session_lines_by_date(self, date: Union[str, RepublicDate]) -> Union[None, rdm.Session]:
        session_index = 'session_lines'
        return self.retrieve_session_by_date(date, session_index)

    def retrieve_session_by_date(self, date: Union[str, RepublicDate],
                                 session_index: str) -> Union[None, rdm.Session]:
        date_string = date.isoformat() if isinstance(date, RepublicDate) else date
        doc_id = f'session-{date_string}-num-1'
        if self.es_anno.exists(index=session_index, id=doc_id):
            response = self.es_anno.get(index=session_index, id=doc_id)
            return rdm.json_to_republic_session(response['_source'])
        else:
            return None

    def retrieve_resolution_by_id(self, resolution_id: str) -> Union[rdm.Resolution, None]:
        if self.es_anno.exists(index=self.config['resolution_index'], id=resolution_id):
            response = self.es_anno.get(index=self.config['resolution_index'], id=resolution_id)
            return rdm.json_to_republic_resolution(response['_source'])
        else:
            return None

    def retrieve_resolutions_by_text_page_number(self, text_page_num: int, year: int = None,
                                                 inventory_num: int = None) -> List[rdm.Resolution]:
        match_fields = [
            {'match': {'metadata.text_page_num': text_page_num}},
            select_year_inv(year=year, inventory_num=inventory_num)
        ]
        query = make_bool_query(match_fields)
        return self.retrieve_resolutions_by_query(query, size=1000)

    def scroll_resolutions_by_query(self, query: dict,
                                    scroll: str = '1m') -> Generator[rdm.Resolution, None, None]:
        for hit in self.scroll_hits(self.es_anno, query, index=self.config['resolution_index'],
                                    doc_type="_doc", size=10, scroll=scroll):
            yield rdm.json_to_republic_resolution(hit['_source'])

    def retrieve_resolutions_by_query(self, query: dict, size: int = 10, aggs: Dict[str, any] = None) -> List[rdm.Resolution]:
        if "query" in query:
            response = self.es_anno.search(index=self.config['resolution_index'], body=query)
        else:
            response = self.es_anno.search(index=self.config['resolution_index'], query=query, aggs=aggs, size=size)
        if response['hits']['total']['value'] == 0:
            return []
        else:
            docs = [hit['_source'] for hit in response['hits']['hits']]
            resolutions = []
            for doc in docs:
                res = rdm.json_to_republic_attendance_list(doc) if 'attendance_list' in doc \
                    else rdm.json_to_republic_resolution(doc)
                resolutions.append(res)
            return resolutions

    def scroll_inventory_resolutions(self, inventory_num: int) -> Generator[rdm.Resolution, None, None]:
        query = make_bool_query([
            {'match': {'metadata.inventory_num': inventory_num}},
            {'match': {'metadata.type': 'resolution'}}
        ])
        for resolution in self.scroll_resolutions_by_query(query, scroll='20m'):
            yield resolution

    def retrieve_attendance_list_by_id(self, att_id: str) -> rdm.AttendanceList:
        if self.es_anno.exists(index=self.config["resolution_index"], id=att_id):
            response = self.es_anno.get(index=self.config["resolution_index"], id=att_id)
            return rdm.json_to_republic_attendance_list(response["_source"])
        else:
            raise ValueError(f"No attendance list exists with id {att_id}")

    def retrieve_attendance_lists_by_query(self, query: dict) -> List[rdm.AttendanceList]:
        response = self.es_anno.search(index=self.config['resolution_index'], body=query)
        return [rdm.json_to_republic_attendance_list(hit['_source']) for hit in response['hits']['hits']]

    def scroll_phrase_matches_by_query(self, query: dict, size: int = 100,
                                       scroll: str = '1m') -> Generator[PhraseMatch, None, None]:
        for hit in self.scroll_hits(self.es_anno, query, index=self.config['phrase_match_index'],
                                    doc_type="_doc", size=size, scroll=scroll):
            match_json = hit['_source']
            yield rdm.parse_phrase_matches([match_json])[0]

    def retrieve_phrase_matches_by_query(self, query: dict) -> List[PhraseMatch]:
        response = self.es_anno.search(index=self.config['phrase_match_index'], doc_type="_doc", body=query)
        if response['hits']['total']['value'] == 0:
            return []
        else:
            return rdm.parse_phrase_matches([hit['_source'] for hit in response['hits']['hits']])

    def retrieve_phrase_matches_by_paragraph_id(self, paragraph_id: str) -> List[PhraseMatch]:
        query = {'query': {'match': {'text_id.keyword': paragraph_id}}, 'size': 1000}
        phrase_matches = self.retrieve_phrase_matches_by_query(query)
        # sort matches by order of occurrence in the text
        return sorted(phrase_matches, key=lambda x: x.offset)

    def retrieve_lemma_references_by_query(self, query: Dict[str, any]) -> List[Dict[str, any]]:
        response = self.es_anno.search(index=self.config["lemma_index"], body=query)
        if "hits" in response["hits"]:
            docs = [hit["_source"] for hit in response["hits"]["hits"]]
        else:
            docs = []
        return docs

    def retrieve_lemma_references_by_lemma(self, lemma: str) -> List[Dict[str, any]]:
        query = {"query": {"match": {"lemma.keyword": lemma}}}
        return self.retrieve_lemma_references_by_query(query)

    def retrieve_lemma_reference_by_id(self, ref_id: str) -> Union[None, Dict[str, any]]:
        if self.es_anno.exists(index=self.config["lemma_index"], id=ref_id):
            return self.es_anno.get(index=self.config["lemma_index"], id=ref_id)
        else:
            return None

    def parse_latest_version(self, text_repo, scan_num,
                             inventory_metadata, ignore_version: bool = False):
        doc_id = get_scan_id(inventory_metadata, scan_num)
        try:
            version_info = text_repo.get_last_version_info(doc_id, file_type=self.config['ocr_type'])
            if not version_info:
                return None
            if not ignore_version and self.es_anno.exists(index=self.config["scan_index"], id=doc_id):
                response = self.es_anno.get(index=self.config["scan_index"], id=doc_id)
                indexed_scan = response["_source"]
                if indexed_scan["version"]["id"] == version_info["id"]:
                    # this version is already indexed
                    return None
            scan_pagexml = text_repo.get_last_version_content(doc_id, self.config['ocr_type'])
            file_extension = '.hocr' if self.config['ocr_type'] == 'hocr' else '.page.xml'
            scan_doc = pagexml_parser.get_scan_pagexml(doc_id + file_extension,
                                                       self.config, pagexml_data=scan_pagexml)
            scan_doc.metadata["version"] = version_info
            return scan_doc
        except ValueError:
            print('missing scan:', doc_id)
            return None

    def keyword_in_context(self, term: str,
                             num_hits: int = 10,
                             context_size: int = 3,
                             index: str = "resolutions",
                             filters: List[Dict[str,any]] = None):
        query = make_paragraph_term_query(term)
        if filters is not None:
            query["query"]["bool"]["must"] += filters
        query['size'] = num_hits
        response = self.es_anno.search(index=index, body=query)
        pre_regex = r'(\w+\W+){,' + f'{context_size}' + r'}\b('
        post_regex = r')\b(\W+\w+){,' + f'{context_size}' + '}'
        pre_width = 5 + context_size * 10
        results = []
        for hit in response['hits']['hits']:
            doc = hit['_source']
            res_start_offset = doc['paragraphs'][0]['metadata']['start_offset']
            for para in doc['paragraphs']:
                para_offset = para['metadata']['start_offset'] - res_start_offset
                for match in re.finditer(pre_regex + term + post_regex, para['text'], re.IGNORECASE):
                    main = match.group(2)
                    pre, post = match.group(0).split(main, 1)
                    if context_size > 6:
                        context = f"{pre}{main}{post}"
                    else:
                        context = f"{pre: >{pre_width}}{main}{post}"
                    result = {
                        'term': term,
                        'term_match': main,
                        'pre': pre,
                        'post': post,
                        'context': context,
                        'para_offset': match.span()[0],
                        'para_id': para["id"],
                        'resolution_id': doc["id"],
                        'resolution_offset': match.span()[0] + para_offset
                    }
                    results.append(result)
        return results

    def print_term_in_context(self, term: str, num_hits: int = 10, context_size: int = 5):
        prev_id = None
        for context in self.keyword_in_context(term, num_hits=num_hits,
                                               context_size=context_size):
            if context['para_id'] != prev_id:
                print('\n', context['para_id'])
            print(context['context'])
            prev_id = context['para_id']

    def get_pagexml_resolution_page_range(self, inv_num: int) -> Union[None, tuple]:
        inv_metadata = self.retrieve_inventory_metadata(inv_num)
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

    def retrieve_date_num_sessions(self, session_date):
        query = {'query': {'match': {'metadata.session_date': str(session_date)}}, 'size': 0}
        response = self.es_anno.search(index=self.config['session_index'], body=query)
        return response['hits']['total']['value']

    def retrieve_resolutions_by_session_date(self, session_date):
        query = {'query': {'match': {'metadata.session_date': str(session_date)}}, 'size': 1000}
        return self.retrieve_resolutions_by_query(query, size=1000)

    def retrieve_resolutions_by_session_id(self, session_id):
        query = {'query': {'match': {'metadata.session_id.keyword': session_id}}, 'size': 1000}
        return self.retrieve_resolutions_by_query(query, size=1000)

    def retrieve_session_phrase_matches(self, session_resolutions):
        paragraph_ids = [paragraph.metadata['id'] for resolution in session_resolutions
                         for paragraph in resolution.paragraphs]
        phrase_matches = []
        for para_id in paragraph_ids:
            query = {'query': {'match': {'text_id.keyword': para_id}}, 'size': 1000}
            phrase_matches += self.retrieve_phrase_matches_by_query(query)
        return phrase_matches
