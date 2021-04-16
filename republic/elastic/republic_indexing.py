import datetime
import json
import copy
import re
from typing import Union, Dict
from elasticsearch import Elasticsearch, RequestError
from fuzzy_search.fuzzy_match import PhraseMatch
from fuzzy_search.fuzzy_phrase_searcher import FuzzyPhraseSearcher
from fuzzy_search.fuzzy_phrase_model import PhraseModel

from republic.extraction.extract_resolution_metadata import generate_proposition_searchers, add_resolution_metadata
from republic.model.physical_document_model import StructureDoc, parse_derived_coords, json_to_pagexml_scan
from republic.model.physical_document_model import PageXMLPage
from settings import text_repo_url
from republic.download.text_repo import TextRepo
import republic.parser.logical.pagexml_session_parser as session_parser
import republic.parser.republic_file_parser as file_parser
import republic.parser.republic_inventory_parser as inv_parser
import republic.parser.hocr.republic_page_parser as hocr_page_parser
import republic.model.resolution_phrase_model as rpm
from republic.model.republic_date import RepublicDate, make_republic_date
from republic.model.republic_document_model import Session, get_session_resolutions, get_session_scans_version
from republic.model.republic_document_model import Resolution, configure_resolution_searchers
from republic.model.republic_document_model import make_session_text_version
from republic.config.republic_config import set_config_inventory_num
from republic.elastic.republic_retrieving import create_es_scan_doc, create_es_page_doc
from republic.helper.metadata_helper import get_per_page_type_index
import republic.parser.pagexml.republic_pagexml_parser as pagexml_parser
from republic.helper.annotation_helper import make_hash_id
import republic.elastic.republic_retrieving as rep_es


def add_timestamp(doc: Union[Dict[str, any], StructureDoc]) -> None:
    if isinstance(doc, StructureDoc):
        doc.metadata['index_timestamp'] = datetime.datetime.now().isoformat()
    else:
        doc['metadata']['index_timestamp'] = datetime.datetime.now().isoformat()


def get_pagexml_page_type(page: Union[PageXMLPage, Dict[str, any]],
                          page_type_index: Dict[str, str]) -> str:
    page_num = page.metadata['page_num'] if isinstance(page, PageXMLPage) else page['metadata']['page_num']
    if page_num not in page_type_index:
        return "empty_page"
    else:
        return page_type_index[page_num]


def add_pagexml_page_types(es: Elasticsearch, inv_config: dict) -> None:
    inv_metadata = rep_es.retrieve_inventory_metadata(es, inv_config["inventory_num"], inv_config)
    page_type_index = get_per_page_type_index(inv_metadata)
    pages = rep_es.retrieve_inventory_pages(es, inv_config["inventory_num"], inv_config)
    for pi, page in enumerate(sorted(pages, key=lambda x: x.metadata['page_num'])):
        page.metadata['page_type'] = get_pagexml_page_type(page, page_type_index)
        add_timestamp(page)
        es.index(index=inv_config["page_index"], id=page.metadata['id'], body=page.json())
        print(page.metadata['id'], page.metadata["page_type"])


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
    add_timestamp(doc)
    es.index(index=config['scan_index'], doc_type=config['scan_doc_type'],
             id=scan_hocr['metadata']['id'], body=doc)


def index_page(es: Elasticsearch, page_hocr: dict, config: dict):
    doc = create_es_page_doc(page_hocr)
    add_timestamp(doc)
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
    inv_metadata = rep_es.retrieve_inventory_metadata(es, inventory_num, inventory_config)
    page_type_index = get_per_page_type_index(inv_metadata)
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
            page_doc.metadata["version"] = version_info
            page_doc.metadata['type'] = [page_doc.metadata['type'], page_type_index[page_doc.metadata['page_num']]]
            index_page(es, page_doc.json, inventory_config)


def index_inventory_from_text_repo(es, inv_num, inventory_config: Dict[str, any], ignore_version: bool = False):
    text_repo = TextRepo(text_repo_url)
    inventory_metadata = rep_es.retrieve_inventory_metadata(es, inv_num, inventory_config)
    page_type_index = get_per_page_type_index(inventory_metadata)
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
            page_doc['metadata']['page_type'] = get_pagexml_page_type(page_doc, page_type_index)
            page_doc["version"] = scan_doc["version"]
            index_page(es, page_doc, inventory_config)


def index_inventory_scans_from_text_repo(es_anno, es_text, inventory_num, config):
    for si, scan_doc in enumerate(rep_es.retrieve_scans_pagexml_from_text_repo_by_inventory(es_text,
                                                                                            inventory_num, config)):
        scan_doc.metadata['index_timestamp'] = datetime.datetime.now()
        es_anno.index(index=config['scan_index'], id=scan_doc.id, body=scan_doc.json)
    return None


def index_inventory_pages_from_scans(es_anno: Elasticsearch, inventory_num: int):
    inv_config = set_config_inventory_num(inventory_num, ocr_type="pagexml")
    inv_metadata = rep_es.retrieve_inventory_metadata(es_anno, inv_config["inventory_num"], inv_config)
    page_type_index = rep_es.get_per_page_type_index(inv_metadata)
    query = rep_es.make_inventory_query(inventory_num)
    del query['size']
    for hi, hit in enumerate(rep_es.scroll_hits(es_anno, query, index='scans', size=2)):
        scan_doc = json_to_pagexml_scan(hit['_source'])
        pages_doc = pagexml_parser.split_pagexml_scan(scan_doc)
        for page_doc in pages_doc:
            if page_doc.metadata['page_num'] not in page_type_index:
                page_doc.metadata['type'] = "empty_page"
                print("page without page_num:", page_doc.id)
                print("\tpage stats:", page_doc.stats)
            else:
                page_doc.metadata['type'] = [page_doc.metadata['type'], page_type_index[page_doc.metadata['page_num']]]
            page_doc.metadata['index_timestamp'] = datetime.datetime.now()
            es_anno.index(index=inv_config['page_index'], id=page_doc.id, body=page_doc.json)
        if (hi+1) % 100 == 0:
            print(hi+1, "scans processed")


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


def index_sessions_inventory(es_anno: Elasticsearch, inv_num: int, inv_config: dict) -> None:
    pages = rep_es.retrieve_resolution_pages(es_anno, inv_num, inv_config)
    pages.sort(key=lambda page: page.metadata['page_num'])
    inv_metadata = rep_es.retrieve_inventory_metadata(es_anno, inv_num, inv_config)
    for mi, session in enumerate(session_parser.get_sessions(pages, inv_config, inv_metadata)):
        session_text_doc = make_session_text_version(session)
        print(session.metadata['id'], session_text_doc['metadata']['id'])
        es_anno.index(index='session_text', id=session.metadata['id'], body=session_text_doc)


def index_sessions_inventory_old(es: Elasticsearch, inv_num: int, inv_config: dict) -> None:
    # pages = retrieve_pagexml_resolution_pages(es, inv_num, inv_config)
    pages = rep_es.retrieve_resolution_pages(es, inv_num, inv_config)
    pages.sort(key=lambda page: page.metadata['page_num'])
    inv_metadata = rep_es.retrieve_inventory_metadata(es, inv_num, inv_config)
    prev_date: RepublicDate = make_republic_date(inv_metadata['period_start'])
    if not pages:
        print('No pages retrieved for inventory', inv_num)
        return None
    for mi, session in enumerate(session_parser.get_sessions(pages, inv_config, inv_metadata)):
        print(json.dumps(session.metadata, indent=4))
        if session.metadata['num_lines'] > 4000:
            # exceptionally long session docs probably contain multiple sessions
            # so quarantine these
            session.metadata['date_shift_status'] = 'quarantined'
            # print('Error: too many lines for session on date', session.metadata['session_date'])
            # continue
        session_date_string = 'None'
        for missing_session in add_missing_dates(prev_date, session):
            add_timestamp(missing_session)
            es.index(index=inv_config['session_index'], doc_type=inv_config['session_doc_type'],
                     id=missing_session.metadata['id'],
                     body=missing_session.json(with_columns=True, with_scan_versions=True))

        session.scan_versions = get_session_scans_version(session)
        session_parser.clean_lines(session.lines, clean_copy=False)
        if session.metadata['has_session_date_element']:
            for evidence in session.evidence:
                if evidence['metadata_field'] == 'session_date':
                    session_date_string = evidence['matches'][-1]['match_string']
        page_num = int(session.columns[0]['metadata']['page_id'].split('page-')[1])
        num_lines = session.metadata['num_lines']
        session_id = session.metadata['id']
        print(
            f"{mi}\t{session_id}\t{session_date_string: <30}\tnum_lines: {num_lines}\tpage: {page_num}")

        # print('Indexing session on date', session.metadata['session_date'],
        #      '\tdate_string:', session_date_string,
        #      '\tnum session lines:', session.metadata['num_lines'])
        prev_date = session.date
        try:
            add_timestamp(session)
            if session.metadata['date_shift_status'] == 'quarantined':
                quarantine_index = inv_config['session_index'] + '_quarantine'
                es.index(index=quarantine_index, doc_type=inv_config['session_doc_type'],
                         id=session.metadata['id'], body=session.json(with_columns=True, with_scan_versions=True))
            else:
                es.index(index=inv_config['session_index'], doc_type=inv_config['session_doc_type'],
                         id=session.metadata['id'], body=session.json(with_columns=True, with_scan_versions=True))
        except RequestError:
            print('skipping doc')
            continue
    return None


def add_missing_dates(prev_date: RepublicDate, session: Session):
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
                    textregion['coords'] = parse_derived_coords(textregion['lines'])
                    keep_textregions += [textregion]
            column['textregions'] = keep_textregions
            if len(column['textregions']) > 0:
                column['coords'] = parse_derived_coords(column['textregions'])
                keep_columns += [column]
        missing_session.columns = keep_columns
        missing_session.metadata['num_columns'] = len(missing_session.columns)
        missing_session.metadata['num_lines'] = num_lines
        missing_session.metadata['num_words'] = num_words
        missing_session.scan_versions = get_session_scans_version(missing_session)
        session_parser.clean_lines(missing_session.lines, clean_copy=False)
        print('missing session:', missing_session.id)
        yield missing_session


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
    for hit in rep_es.scroll_hits(es, query, index=inv_config['session_index'], doc_type="session", size=2):
        print(hit['_id'])
        session_json = hit['_source']
        session = Session(session_json['metadata'], columns=session_json['columns'],
                          scan_versions=session_json['scan_versions'])
        for resolution in get_session_resolutions(session, opening_searcher, verb_searcher):
            add_timestamp(resolution)
            es.index(index=inv_config['resolution_index'], id=resolution.metadata['id'], body=resolution.json())


def index_session_resolutions(es: Elasticsearch, session: Session, opening_searcher: FuzzyPhraseSearcher,
                              verb_searcher: FuzzyPhraseSearcher, inv_config: dict) -> None:
    for resolution in get_session_resolutions(session, opening_searcher, verb_searcher):
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
    add_timestamp(resolution)
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


def index_inventory_resolution_metadata(es: Elasticsearch, inv_config: dict):
    proposition_searcher, template_searcher, variable_matcher = generate_proposition_searchers()
    skip_formulas = {
        'heeft aan haar Hoog Mog. voorgedragen',
        'heeft ter Vergadering gecommuniceert ',
        'ZYnde ter Vergaderinge geëxhibeert vier Pasporten van',
        'hebben ter Vergaderinge ingebraght',
        'hebben ter Vergaderinge voorgedragen'
    }
    for resolution in rep_es.scroll_inventory_resolutions(es, inv_config):
        if resolution.evidence[0].phrase.phrase_string in skip_formulas:
            continue
        new_resolution = add_resolution_metadata(resolution, proposition_searcher,
                                                 template_searcher, variable_matcher)
        if not new_resolution:
            continue
        print('indexing metadata for resolution', resolution.metadata['id'])
        # print(new_resolution.metadata)
        index_resolution_metadata(es, new_resolution, inv_config)


def index_resolution_phrase_match(es: Elasticsearch, phrase_match: Union[dict, PhraseMatch], config: dict):
    # make sure match object is json dictionary
    match_json = phrase_match.json() if isinstance(phrase_match, PhraseMatch) else phrase_match
    # generate stable id based on match offset, end and text_id
    match_json['id'] = make_hash_id(match_json)
    add_timestamp(match_json)
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

    phrases = rpm.proposition_opening_phrases
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
        add_timestamp(resolution)
        index_resolution(es, resolution, config)


def index_resolution_metadata(es: Elasticsearch, resolution: Resolution, config: dict):
    metadata_doc = {
        'metadata': resolution.metadata,
        'evidence': [pm.json() for pm in resolution.evidence]
    }
    add_timestamp(metadata_doc)
    es.index(index=config['resolution_metadata_index'], id=resolution.metadata['id'], body=metadata_doc)
