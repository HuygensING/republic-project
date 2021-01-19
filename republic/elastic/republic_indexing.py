import datetime
import json
import copy
import re
from typing import Union, Dict
from elasticsearch import Elasticsearch, RequestError
from fuzzy_search.fuzzy_match import PhraseMatch
from fuzzy_search.fuzzy_phrase_searcher import FuzzyPhraseSearcher
from fuzzy_search.fuzzy_phrase_model import PhraseModel

from settings import text_repo_url
from republic.download.text_repo import TextRepo
import republic.parser.pagexml.pagexml_meeting_parser as meeting_parser
import republic.parser.republic_file_parser as file_parser
import republic.parser.republic_inventory_parser as inv_parser
import republic.parser.hocr.republic_base_page_parser as hocr_base_parser
import republic.parser.hocr.republic_page_parser as hocr_page_parser
import republic.parser.hocr.republic_paragraph_parser as hocr_para_parser
import republic.model.resolution_phrase_model as rpm
from republic.model.republic_date import RepublicDate, make_republic_date
from republic.model.republic_hocr_model import HOCRPage
from republic.model.republic_phrase_model import category_index
from republic.model.republic_pagexml_model import parse_derived_coords
from republic.model.republic_document_model import Meeting, get_meeting_resolutions, Resolution
from republic.config.republic_config import set_config_inventory_num
from republic.fuzzy.fuzzy_context_searcher import FuzzyContextSearcher
from republic.elastic.republic_retrieving import create_es_scan_doc, create_es_page_doc
from republic.helper.metadata_helper import get_per_page_type_index
import republic.parser.pagexml.republic_pagexml_parser as pagexml_parser
from republic.helper.annotation_helper import make_hash_id
import republic.elastic.republic_retrieving as rep_es


def add_pagexml_page_types(es: Elasticsearch, inv_config: dict) -> None:
    inv_metadata = rep_es.retrieve_inventory_metadata(es, inv_config["inventory_num"], inv_config)
    page_type_index = get_per_page_type_index(inv_metadata)
    pages = rep_es.retrieve_inventory_pages(es, inv_config["inventory_num"], inv_config)
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


def clone_index(es: Elasticsearch, original_index: str, new_index: str):
    # 1. make sure the clone index doesn't exist
    if es.indices.exists(index=new_index):
        # raise ValueError("index already exists")
        print("deleting clone index:", new_index)
        print(es.indices.delete(index=new_index))
    # 2. set original index to read-only
    print(f"setting original index {original_index} to read-only")
    print(es.indices.put_settings(index=original_index, body={"index.blocks.write": True}))
    # 3. clone the index
    print(f"cloning original index {original_index} to {new_index}")
    print(es.indices.clone(index=original_index, target=new_index))
    # 4. set original index to read-write
    print(f"setting original index {original_index} to read-write")
    print(es.indices.put_settings(index=original_index, body={"index.blocks.write": False}))


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
        lemma_doc = rep_es.create_es_index_lemma_doc(lemma, lemma_index, config)
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
    text_repo = TextRepo(text_repo_url)
    for scan_doc in inv_parser.parse_inventory_from_zip(inventory_num, inventory_config):
        version_info = text_repo.get_last_version_info(scan_doc["metadata"]["id"],
                                                       file_type=inventory_config['ocr_type'])
        scan_doc["version"] = version_info
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
            page_doc["version"] = version_info
            index_page(es, page_doc, inventory_config)


def index_inventory_from_text_repo(es, inv_num, inventory_config: Dict[str, any], ignore_version: bool = False):
    text_repo = TextRepo(text_repo_url)
    inventory_metadata = rep_es.retrieve_inventory_metadata(es, inv_num, inventory_config)
    if "num_scans" not in inventory_metadata:
        return None
    for scan_num in range(1, inventory_metadata["num_scans"] + 1):
        scan_doc = rep_es.parse_latest_version(es, text_repo, scan_num, inventory_metadata,
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
    inventory_config = set_config_inventory_num(inventory_num, ocr_type="hocr",
                                                default_config=base_config, base_dir=base_dir)
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
    scans_hocr: list = rep_es.retrieve_inventory_hocr_scans(es, inventory_num, config)
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
    page_docs = rep_es.retrieve_resolution_pages(es, inventory_num, inventory_config)
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


def index_meetings_inventory(es: Elasticsearch, inv_num: int, inv_config: dict) -> None:
    # pages = retrieve_pagexml_resolution_pages(es, inv_num, inv_config)
    pages = rep_es.retrieve_resolution_pages(es, inv_num, inv_config)
    pages.sort(key=lambda page: page['metadata']['page_num'])
    inv_metadata = rep_es.retrieve_inventory_metadata(es, inv_num, inv_config)
    prev_date: RepublicDate = make_republic_date(inv_metadata['period_start'])
    if not pages:
        print('No pages retrieved for inventory', inv_num)
        return None
    for mi, meeting in enumerate(meeting_parser.get_meeting_dates(pages, inv_config, inv_metadata)):
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
                     id=missing_meeting.metadata['id'],
                     body=missing_meeting.json(with_columns=True, with_scan_versions=True))

        meeting.scan_versions = meeting_parser.get_meeting_scans_version(meeting)
        meeting_parser.clean_lines(meeting.lines, clean_copy=False)
        if meeting.metadata['has_meeting_date_element']:
            for evidence in meeting.metadata['evidence']:
                if evidence['metadata_field'] == 'meeting_date':
                    meeting_date_string = evidence['matches'][-1]['match_string']
        page_num = int(meeting.columns[0]['metadata']['page_id'].split('page-')[1])
        num_lines = meeting.metadata['num_lines']
        meeting_id = meeting.metadata['id']
        print(
            f"{mi}\t{meeting_id}\t{meeting_date_string: <30}\tnum_lines: {num_lines}\tpage: {page_num}")

        # print('Indexing meeting on date', meeting.metadata['meeting_date'],
        #      '\tdate_string:', meeting_date_string,
        #      '\tnum meeting lines:', meeting.metadata['num_lines'])
        prev_date = meeting.date
        try:
            meeting.metadata['index_timestamp'] = datetime.datetime.now()
            if meeting.metadata['date_shift_status'] == 'quarantined':
                quarantine_index = inv_config['meeting_index'] + '_quarantine'
                es.index(index=quarantine_index, doc_type=inv_config['meeting_doc_type'],
                         id=meeting.metadata['id'], body=meeting.json(with_columns=True, with_scan_versions=True))
            else:
                es.index(index=inv_config['meeting_index'], doc_type=inv_config['meeting_doc_type'],
                         id=meeting.metadata['id'], body=meeting.json(with_columns=True, with_scan_versions=True))
        except RequestError:
            print('skipping doc')
            continue
    return None


def add_missing_dates(prev_date: RepublicDate, meeting: Meeting):
    missing = (meeting.date - prev_date).days - 1
    if missing > 0:
        print('missing days:', missing)
    for diff in range(1, missing + 1):
        # create a new meeting doc for the missing date, with data copied from the current meeting
        # as most likely the missing date is a non-meeting date with 'nihil actum est'
        missing_date = prev_date.date + datetime.timedelta(days=diff)
        missing_date = RepublicDate(missing_date.year, missing_date.month, missing_date.day)
        missing_meeting = copy.deepcopy(meeting)
        missing_meeting.metadata['id'] = f'meeting-{missing_date.isoformat()}-session-1'
        missing_meeting.id = missing_meeting.metadata['id']
        missing_meeting.metadata['meeting_date'] = missing_date.isoformat()
        missing_meeting.metadata['year'] = missing_date.year
        missing_meeting.metadata['meeting_month'] = missing_date.month
        missing_meeting.metadata['meeting_day'] = missing_date.day
        missing_meeting.metadata['meeting_weekday'] = missing_date.day_name
        missing_meeting.metadata['is_workday'] = missing_date.is_work_day()
        missing_meeting.metadata['session'] = None
        missing_meeting.metadata['president'] = None
        missing_meeting.metadata['attendants_list_id'] = None
        evidence_lines = set([evidence['line_id'] for evidence in missing_meeting.metadata['evidence']])
        keep_columns = []
        num_lines = 0
        num_words = 0
        missing_meeting.lines = []
        for column in missing_meeting.columns:
            keep_textregions = []
            for textregion in column['textregions']:
                keep_lines = []
                for line in textregion['lines']:
                    if len(evidence_lines) > 0:
                        keep_lines += [line]
                        missing_meeting.lines += [line]
                        num_lines += 1
                        if line['text']:
                            num_words += len([word for word in re.split(r'\W+', line['text']) if word != ''])
                    else:
                        break
                    if line['metadata']['id'] in evidence_lines:
                        evidence_lines.remove(line['metadata']['id'])
                textregion['lines'] = keep_lines
                if len(textregion['lines']) > 0:
                    textregion['coords'] = parse_derived_coords(textregion['lines'])
                    keep_textregions += [textregion]
            column['textregions'] = keep_textregions
            if len(column['textregions']) > 0:
                column['coords'] = parse_derived_coords(column['textregions'])
                keep_columns += [column]
        missing_meeting.columns = keep_columns
        missing_meeting.metadata['num_columns'] = len(missing_meeting.columns)
        missing_meeting.metadata['num_lines'] = num_lines
        missing_meeting.metadata['num_words'] = num_words
        missing_meeting.scan_versions = meeting_parser.get_meeting_scans_version(missing_meeting)
        meeting_parser.clean_lines(missing_meeting.lines, clean_copy=False)
        print('missing meeting:', missing_meeting.id)
        yield missing_meeting


def configure_resolution_searchers():
    opening_searcher_config = {
        'filter_distractors': True,
        'include_variants': True,
        'max_length_variance': 3
    }
    opening_searcher = FuzzyPhraseSearcher(opening_searcher_config)
    opening_phrase_model = PhraseModel(model=rpm.proposition_opening_phrases)
    opening_searcher.index_phrase_model(opening_phrase_model)
    verb_searcher_config = {
        'max_length_variance': 1
    }
    verb_searcher = FuzzyPhraseSearcher(verb_searcher_config)
    verb_phrase_model = PhraseModel(model=rpm.proposition_verbs)
    verb_searcher.index_phrase_model(verb_phrase_model)
    return opening_searcher, verb_searcher


def index_inventory_resolutions(es: Elasticsearch, inv_config: dict):
    opening_searcher, verb_searcher = configure_resolution_searchers()
    query = {
        'query': {
            'bool': {
                'must': [
                    {'match': {'metadata.inventory_num': inv_config['inventory_num']}}
                ]
            }
        }
    }
    for hit in rep_es.scroll_hits(es, query, index=inv_config['meeting_index'], doc_type="meeting", size=2):
        print(hit['_id'])
        meeting_json = hit['_source']
        meeting = Meeting(meeting_json['metadata'], columns=meeting_json['columns'],
                          scan_versions=meeting_json['scan_versions'])
        for resolution in get_meeting_resolutions(meeting, opening_searcher, verb_searcher):
            es.index(index=inv_config['resolution_index'], id=resolution.metadata['id'], body=resolution.json())


def index_meeting_resolutions(es: Elasticsearch, meeting: Meeting, opening_searcher: FuzzyPhraseSearcher,
                              verb_searcher: FuzzyPhraseSearcher, inv_config: dict) -> None:
    for resolution in get_meeting_resolutions(meeting, opening_searcher, verb_searcher):
        index_resolution(es, resolution, inv_config)


def index_resolution(es: Elasticsearch, resolution: Union[dict, Resolution], config: dict):
    """Index an individual resolution.

    :param es: the elasticsearch instance to use for indexing
    :type es: Elasticsearch
    :param resolution: the resolution to index, either Resolution class instance or a dictionary
    :type resolution: Union[Resolution, dict]
    :param config: a configuration dictionary containing index names
    :type config: dict
    """
    resolution_json = resolution.json() if isinstance(resolution, Resolution) else resolution
    es.index(index=config['resolution_index'], id=resolution_json['metadata']['id'], body=resolution_json)


def index_resolution_phrase_matches(es: Elasticsearch, inv_config: dict):
    searcher = make_resolution_phrase_model_searcher()
    for resolution in rep_es.scroll_inventory_resolutions(es, inv_config):
        print('indexing phrase matches for resolution', resolution.metadata['id'])
        for paragraph in resolution.paragraphs:
            doc = {'id': paragraph.metadata['id'], 'text': paragraph.text}
            for match in searcher.find_matches(doc):
                index_resolution_phrase_match(es, match, inv_config)


def index_resolution_phrase_match(es: Elasticsearch, phrase_match: Union[dict, PhraseMatch], config: dict):
    # make sure match object is json dictionary
    match_json = phrase_match.json() if isinstance(phrase_match, PhraseMatch) else phrase_match
    # generate stable id based on match offset, end and text_id
    match_json['id'] = make_hash_id(match_json)
    es.index(index=config['phrase_match_index'], id=match_json['id'], body=match_json)


def delete_resolution_phrase_match(es: Elasticsearch, phrase_match: Union[dict, PhraseMatch], config: dict):
    # make sure match object is json dictionary
    match_json = phrase_match.json() if isinstance(phrase_match, PhraseMatch) else phrase_match
    # generate stable id based on match offset, end and text_id
    match_json['id'] = make_hash_id(match_json)
    if es.exists(index=config['phrase_match_index'], id=match_json['id']):
        es.delete(index=config['phrase_match_index'], id=match_json['id'])
    else:
        raise ValueError(f'unknown phrase match id {match_json["id"]}, phrase match cannot be removed')


def make_resolution_phrase_model_searcher() -> FuzzyPhraseSearcher:
    resolution_phrase_searcher_config = {
        'filter_distractors': True,
        'include_variants': True,
        'max_length_variance': 3,
        'levenshtein_threshold': 0.7,
        'char_match_threshold': 0.7
    }
    resolution_phrase_searcher = FuzzyPhraseSearcher(resolution_phrase_searcher_config)

    phrases = rpm.proposition_reason_phrases + rpm.proposition_closing_phrases + rpm.decision_phrases + \
              rpm.resolution_link_phrases + rpm.prefix_phrases + rpm.organisation_phrases + \
              rpm.location_phrases + rpm.esteem_titles + rpm.person_role_phrases + rpm.military_phrases + \
              rpm.misc + rpm.provinces + rpm.proposition_opening_phrases

    for phrase in phrases:
        if 'max_offset' in phrase:
            del phrase['max_offset']

    resolution_phrase_phrase_model = PhraseModel(model=phrases)
    resolution_phrase_searcher.index_phrase_model(resolution_phrase_phrase_model)
    return resolution_phrase_searcher


def index_split_resolutions(es: Elasticsearch, split_resolutions: Dict[str, any], config: dict):
    for remove_match in split_resolutions['remove_matches']:
        try:
            delete_resolution_phrase_match(es, remove_match, config)
        except ValueError:
            continue
    for add_match in split_resolutions['add_matches']:
        index_resolution_phrase_match(es, add_match, config)
    for resolution in split_resolutions['resolutions']:
        resolution.metadata['index_timestamp'] = datetime.datetime.now().isoformat()
        index_resolution(es, resolution, config)
