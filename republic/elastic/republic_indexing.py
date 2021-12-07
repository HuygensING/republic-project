import datetime
import copy
import re
from typing import Union, Dict, List
from elasticsearch import Elasticsearch
from fuzzy_search.fuzzy_match import PhraseMatch

import republic.parser.logical.pagexml_session_parser as session_parser
import republic.model.republic_document_model as rdm
import republic.model.physical_document_model as pdm
from republic.model.republic_date import RepublicDate
from republic.helper.metadata_helper import get_per_page_type_index
from republic.helper.annotation_helper import make_hash_id


def add_timestamp(doc: Union[Dict[str, any], pdm.StructureDoc]) -> None:
    if isinstance(doc, pdm.StructureDoc):
        doc.metadata['index_timestamp'] = datetime.datetime.now().isoformat()
    else:
        doc['metadata']['index_timestamp'] = datetime.datetime.now().isoformat()


def get_pagexml_page_type(page: Union[pdm.PageXMLPage, Dict[str, any]],
                          page_type_index: Dict[str, str]) -> str:
    page_num = page.metadata['page_num'] if isinstance(page, pdm.PageXMLPage) else page['metadata']['page_num']
    if page_num not in page_type_index:
        return "empty_page"
    else:
        return page_type_index[page_num]


def normalize_lemma(lemma: str) -> str:
    lemma = lemma.replace(' ', '_').replace('/', '_').replace('ê', 'e')
    return lemma


def add_missing_dates(prev_date: RepublicDate, session: rdm.Session):
    missing = (session.date - prev_date).days - 1
    if missing > 0:
        print('missing days:', missing)
    for diff in range(1, missing + 1):
        # create a new meeting doc for the missing date, with data copied from the current meeting
        # as most likely the missing date is a non-meeting date with 'nihil actum est'
        missing_date = prev_date.date + datetime.timedelta(days=diff)
        missing_date = RepublicDate(missing_date.year, missing_date.month, missing_date.day)
        missing_session = copy.deepcopy(session)
        missing_session.metadata['id'] = f'session-{missing_date.isoformat()}-session-1'
        missing_session.id = missing_session.metadata['id']
        missing_session.metadata['session_date'] = missing_date.isoformat()
        missing_session.metadata['year'] = missing_date.year
        missing_session.metadata['session_month'] = missing_date.month
        missing_session.metadata['session_day'] = missing_date.day
        missing_session.metadata['session_weekday'] = missing_date.day_name
        missing_session.metadata['is_workday'] = missing_date.is_work_day()
        missing_session.metadata['session'] = None
        missing_session.metadata['president'] = None
        missing_session.metadata['attendants_list_id'] = None
        evidence_lines = set([evidence['line_id'] for evidence in missing_session.evidence])
        keep_columns = []
        num_lines = 0
        num_words = 0
        missing_session.lines = []
        for column in missing_session.columns:
            keep_textregions = []
            for textregion in column['textregions']:
                keep_lines = []
                for line in textregion['lines']:
                    if len(evidence_lines) > 0:
                        keep_lines += [line]
                        missing_session.lines += [line]
                        num_lines += 1
                        if line['text']:
                            num_words += len([word for word in re.split(r'\W+', line['text']) if word != ''])
                    else:
                        break
                    if line['metadata']['id'] in evidence_lines:
                        evidence_lines.remove(line['metadata']['id'])
                textregion['lines'] = keep_lines
                if len(textregion['lines']) > 0:
                    textregion['coords'] = pdm.parse_derived_coords(textregion['lines'])
                    keep_textregions += [textregion]
            column['textregions'] = keep_textregions
            if len(column['textregions']) > 0:
                column['coords'] = pdm.parse_derived_coords(column['textregions'])
                keep_columns += [column]
        missing_session.columns = keep_columns
        missing_session.metadata['num_columns'] = len(missing_session.columns)
        missing_session.metadata['num_lines'] = num_lines
        missing_session.metadata['num_words'] = num_words
        missing_session.scan_versions = session_parser.get_session_scans_version(missing_session)
        session_parser.clean_lines(missing_session.lines, clean_copy=False)
        print('missing session:', missing_session.id)
        yield missing_session


class Indexer:

    def __init__(self, es_anno: Elasticsearch, es_text: Elasticsearch, config: dict):
        self.es_anno = es_anno
        self.es_text = es_text
        self.config = config

    def index_doc(self, index: str, doc_id: str, doc_body: dict):
        add_timestamp(doc_body)
        self.es_anno.index(index=index, id=doc_id, body=doc_body)

    def index_scan(self, scan: pdm.PageXMLScan):
        self.index_doc(index=self.config['scan_index'], doc_id=scan.id, doc_body=scan.json)

    def index_page(self, page: pdm.PageXMLPage):
        self.index_doc(index=self.config['page_index'], doc_id=page.id, doc_body=page.json)

    def index_inventory_metadata(self, inventory_metadata: dict):
        self.index_doc(index=self.config['inventory_index'],
                       doc_id=inventory_metadata['inventory_num'],
                       doc_body=inventory_metadata)

    def index_session_with_lines(self, session: rdm.Session):
        self.index_doc(index=self.config['session_text_index'],
                       doc_id=session.id,
                       doc_body=session.json)

    def index_session_with_text(self, session_text_doc: dict):
        self.index_doc(index=self.config['session_text_index'],
                       doc_id=session_text_doc["metadata"]["id"],
                       doc_body=session_text_doc)

    def index_resolution(self, resolution: rdm.Resolution):
        print('\t', resolution.id, resolution.paragraphs[0].text[:60])
        self.index_doc(index=self.config['resolution_index'],
                       doc_id=resolution.metadata['id'],
                       doc_body=resolution.json)

    def index_attendance_list(self, attendance_list: rdm.AttendanceList):
        self.es_anno.index(index=self.config["resolution_index"],
                           id=attendance_list.id,
                           body=attendance_list.json)

    def index_resolution_metadata(self, resolution: rdm.Resolution):
        metadata_copy: Dict[str, any] = copy.deepcopy(resolution.metadata)
        metadata_doc = {
            'metadata': metadata_copy,
            'evidence': [pm.json() for pm in resolution.evidence]
        }
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
        match_json['id'] = make_hash_id(match_json)
        match_json['metadata'] = phrase_match.phrase.metadata
        match_json['metadata']['id'] = match_json['id']
        match_json['metadata']['resolution_id'] = resolution.id
        match_json['metadata']['session_id'] = resolution.metadata['session_id']
        match_json['metadata']['paragraph_id'] = phrase_match.text_id
        add_timestamp(match_json)
        # print(json.dumps(match_json, indent=2))
        self.index_doc(index=self.config['phrase_match_index'],
                       doc_id=match_json['id'],
                       doc_body=match_json)

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
        match_json['id'] = make_hash_id(match_json)
        if self.es_anno.exists(index=self.config['phrase_match_index'], id=match_json['id']):
            self.es_anno.delete(index=self.config['phrase_match_index'], id=match_json['id'])
        else:
            raise ValueError(f'unknown phrase match id {match_json["id"]}, phrase match cannot be removed')

    def delete_es_index(self, index: str):
        if self.es_anno.indices.exists(index=index):
            print(f' index{index} exists, deleting')
            self.es_anno.indices.delete(index=index)

    def clone_index(self, original_index: str, new_index: str) -> None:
        # 1. make sure the clone index doesn't exist
        if self.es_anno.indices.exists(index=new_index):
            # raise ValueError("index already exists")
            print("deleting clone index:", new_index)
            print(self.es_anno.indices.delete(index=new_index))
        # 2. set original index to read-only
        print(f"setting original index {original_index} to read-only")
        print(self.es_anno.indices.put_settings(index=original_index, body={"index.blocks.write": True}))
        # 3. clone the index
        print(f"cloning original index {original_index} to {new_index}")
        print(self.es_anno.indices.clone(index=original_index, target=new_index))
        # 4. set original index to read-write
        print(f"setting original index {original_index} to read-write")
        print(self.es_anno.indices.put_settings(index=original_index, body={"index.blocks.write": False}))
