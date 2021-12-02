import datetime
import copy
import re
from typing import Union, Dict
from elasticsearch import Elasticsearch, RequestError
from fuzzy_search.fuzzy_match import PhraseMatch
from fuzzy_search.fuzzy_phrase_searcher import FuzzyPhraseSearcher
from fuzzy_search.fuzzy_phrase_model import PhraseModel

from republic.config.republic_config import set_config_inventory_num
from republic.extraction.extract_resolution_metadata import generate_proposition_searchers
from republic.extraction.extract_resolution_metadata import add_resolution_metadata
from republic.extraction.extract_resolution_metadata import get_paragraph_phrase_matches
import republic.parser.logical.pagexml_session_parser as session_parser
import republic.model.resolution_phrase_model as rpm
import republic.parser.pagexml.republic_pagexml_parser as pagexml_parser
import republic.elastic.republic_retrieving as rep_es
import run_attendancelist
from republic.model.physical_document_model import StructureDoc, parse_derived_coords, json_to_pagexml_scan
from republic.model.physical_document_model import PageXMLPage
from republic.model.republic_date import RepublicDate
from republic.model.republic_document_model import Session, get_session_resolutions, get_session_scans_version
from republic.model.republic_document_model import Resolution, configure_resolution_searchers
from republic.model.republic_text_annotation_model import make_session_text_version
from republic.helper.metadata_helper import get_per_page_type_index, map_text_page_nums
from republic.helper.annotation_helper import make_hash_id


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
        print(f' index{index} exists, deleting')
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


def index_inventory_scans_from_text_repo(es_anno, es_text, inventory_num, config):
    for si, scan_doc in enumerate(rep_es.retrieve_scans_pagexml_from_text_repo_by_inventory(es_text,
                                                                                            inventory_num, config)):
        scan_doc.metadata['index_timestamp'] = datetime.datetime.now()
        es_anno.index(index=config['scan_index'], id=scan_doc.id, body=scan_doc.json)
    return None


def index_inventory_pages_from_scans(es_anno: Elasticsearch, inventory_num: int):
    inv_config = set_config_inventory_num(inventory_num, ocr_type="pagexml")
    inv_metadata = rep_es.retrieve_inventory_metadata(es_anno, inv_config["inventory_num"], inv_config)
    page_type_index = get_per_page_type_index(inv_metadata)
    text_page_num_map = map_text_page_nums(inv_metadata)
    query = rep_es.make_inventory_query(inventory_num)
    del query['size']
    for hi, hit in enumerate(rep_es.scroll_hits(es_anno, query, index='scans', size=2)):
        scan_doc = json_to_pagexml_scan(hit['_source'])
        pages_doc = pagexml_parser.split_pagexml_scan(scan_doc)
        for page_doc in pages_doc:
            if page_doc.metadata['page_num'] in text_page_num_map:
                page_num = page_doc.metadata['page_num']
                page_doc.metadata['text_page_num'] = text_page_num_map[page_num]['text_page_num']
                if text_page_num_map[page_num]['problem'] is not None:
                    page_doc.metadata['problem'] = text_page_num_map[page_num]['problem']
            if page_doc.metadata['page_num'] not in page_type_index:
                page_doc.add_type("empty_page")
                page_doc.metadata['type'] = [ptype for ptype in page_doc.type]
                print("page without page_num:", page_doc.id)
                print("\tpage stats:", page_doc.stats)
            else:
                page_types = page_type_index[page_doc.metadata['page_num']]
                if isinstance(page_types, str):
                    page_types = [page_types]
                for page_type in page_types:
                    page_doc.add_type(page_type)
                page_doc.metadata['type'] = [ptype for ptype in page_doc.type]
            page_doc.metadata['index_timestamp'] = datetime.datetime.now()
            es_anno.index(index=inv_config['page_index'], id=page_doc.id, body=page_doc.json)
        if (hi+1) % 100 == 0:
            print(hi+1, "scans processed")


def index_inventory_sessions_with_lines(es_anno: Elasticsearch, inv_num: int, config: dict) -> None:
    inv_metadata = rep_es.retrieve_inventory_metadata(es_anno, inv_num, config)
    pages = rep_es.retrieve_resolution_pages(es_anno, inv_num, config)
    pages.sort(key=lambda page: page.metadata['page_num'])
    for mi, session in enumerate(session_parser.get_sessions(pages, config, inv_metadata)):
        print('session received from get_sessions:', session.id)
        date_string = None
        for match in session.evidence:
            if match.has_label('session_date'):
                date_string = match.string
        print('\tdate string:', date_string)
        es_anno.index(index='session_lines', id=session.id, body=session.json)


def index_inventory_sessions_with_text(es_anno: Elasticsearch, inv_num: int, config: dict) -> None:
    from collections import Counter
    for mi, session in enumerate(rep_es.retrieve_inventory_sessions_with_lines(es_anno, inv_num, config)):
        resolutions = rep_es.retrieve_resolutions_by_session_id(es_anno, session.id, config)
        session_text_doc = make_session_text_version(session, resolutions)
        session_text_doc['metadata']['index_timestamp'] = datetime.datetime.now().isoformat()
        type_freq = Counter([anno['type'] for anno in session_text_doc['annotations']])
        for anno_type, freq in type_freq.most_common():
            print(f'{anno_type: <20}{freq: >4}')
        print(session.id, session_text_doc['metadata']['index_timestamp'])
        es_anno.index(index=config['session_text_index'], id=session.id, body=session_text_doc)


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
    print(query)
    print(inv_config['session_lines_index'])
    for session in rep_es.retrieve_inventory_sessions_with_lines(es, inv_config['inventory_num'], inv_config):
        print(session.id)
        # print(session.metadata)
        for resolution in get_session_resolutions(session, opening_searcher, verb_searcher):
            add_timestamp(resolution)
            print('\t', resolution.id, resolution.paragraphs[0].text[:60])
            es.index(index=inv_config['resolution_index'], id=resolution.metadata['id'], body=resolution.json)


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
    resolution_json = resolution.json if isinstance(resolution, Resolution) else resolution
    es.index(index=config['resolution_index'], id=resolution_json['metadata']['id'], body=resolution_json)


def index_attendance_list_spans(es, year, config):
    att_spans_year = run_attendancelist.run(es, year, outdir=None, verbose=True, tofile=False)
    for span_list in att_spans_year:
        att_id = f'{span_list["metadata"]["zittingsdag_id"]}-attendance_list'
        att_list = rep_es.retrieve_attendance_list_by_id(es, att_id, config)
        att_list.attendance_spans = span_list["spans"]
        es.index(index=config["resolution_index"], id=att_list.id, body=att_list.json)


def index_resolution_phrase_matches(es: Elasticsearch, inv_config: dict):
    searcher = make_resolution_phrase_model_searcher()
    print(searcher.config)
    for resolution in rep_es.scroll_inventory_resolutions(es, inv_config):
        print('indexing phrase matches for resolution', resolution.metadata['id'])
        num_paras = len(resolution.paragraphs)
        num_matches = 0
        for paragraph in resolution.paragraphs:
            doc = {'id': paragraph.metadata['id'], 'text': paragraph.text}
            for match in searcher.find_matches(doc):
                index_resolution_phrase_match(es, match, resolution, inv_config)
                num_matches += 1
        print(f'\tparagraphs: {num_paras}\tnum matches: {num_matches}')


def index_inventory_resolution_metadata(es: Elasticsearch, inv_config: dict):
    prop_searchers = generate_proposition_searchers()
    # proposition_searcher, template_searcher, variable_matcher = generate_proposition_searchers()
    skip_formulas = {
        'heeft aan haar Hoog Mog. voorgedragen',
        'heeft ter Vergadering gecommuniceert ',
        # 'ZYnde ter Vergaderinge geëxhibeert vier Pasporten van',
        # 'hebben ter Vergaderinge ingebraght',
        # 'hebben ter Vergaderinge voorgedragen'
    }
    attendance = 0
    no_new = 0
    for ri, resolution in enumerate(rep_es.scroll_inventory_resolutions(es, inv_config)):
        if resolution.metadata['type'] == 'attendance_list':
            attendance += 1
            continue
        if len(resolution.evidence) == 0:
            print('resolution without evidence:', resolution.metadata)
        if resolution.evidence[0].phrase.phrase_string in skip_formulas:
            print(resolution.id)
            print(resolution.paragraphs[0].text)
            print(resolution.evidence[0])
            print()
            # continue
        phrase_matches = get_paragraph_phrase_matches(es, resolution, inv_config)
        new_resolution = add_resolution_metadata(resolution, phrase_matches,
                                                 prop_searchers['template'], prop_searchers['variable'])
        if 'proposition_type' not in new_resolution.metadata or new_resolution.metadata['proposition_type'] is None:
            new_resolution.metadata['proposition_type'] = 'unknown'
        if not new_resolution:
            no_new += 1
            continue
        # print(new_resolution.metadata)
        if (ri+1) % 10 == 0:
            print(ri+1, 'resolutions parsed\t', attendance, 'attendance lists\t', no_new, 'non-metadata')
        index_resolution_metadata(es, new_resolution, inv_config)


def index_resolution_phrase_match(es: Elasticsearch, phrase_match: Union[dict, PhraseMatch],
                                  resolution: Resolution, config: dict):
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
        'use_word_boundaries': True,
        'max_length_variance': 3,
        'levenshtein_threshold': 0.7,
        'char_match_threshold': 0.7,
        'ngram_size': 3,
        'skip_size': 1
    }
    resolution_phrase_searcher = FuzzyPhraseSearcher(resolution_phrase_searcher_config)

    '''
    phrases = rpm.proposition_reason_phrases + rpm.proposition_closing_phrases + rpm.decision_phrases + \
              rpm.resolution_link_phrases + rpm.prefix_phrases + rpm.organisation_phrases + \
              rpm.location_phrases + rpm.esteem_titles + rpm.person_role_phrases + rpm.military_phrases + \
              rpm.misc + rpm.provinces + rpm.proposition_opening_phrases
    '''

    phrases = []
    for set_name in rpm.resolution_phrase_sets:
        print('adding phrases from set', set_name)
        phrases += rpm.resolution_phrase_sets[set_name]
    # phrases = rpm.proposition_opening_phrases
    # for phrase in phrases:
    #     if 'max_offset' in phrase:
    #         del phrase['max_offset']
    print(f'building phrase model for {len(phrases)} resolution phrases')

    resolution_phrase_phrase_model = PhraseModel(model=phrases, config=resolution_phrase_searcher_config)
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
    metadata_copy: Dict[str, any] = copy.deepcopy(resolution.metadata)
    metadata_doc = {
        'metadata': metadata_copy,
        'evidence': [pm.json() for pm in resolution.evidence]
    }
    metadata_doc['metadata']['id'] = metadata_doc['metadata']['id'] + '-metadata'
    add_timestamp(metadata_doc)
    print('indexing metadata for resolution', metadata_doc['metadata']['id'])
    es.index(index=config['resolution_metadata_index'], id=metadata_doc['metadata']['id'], body=metadata_doc)
