from __future__ import annotations
import datetime
import glob
import gzip
import json
import logging
import logging.config
import multiprocessing
import os
from collections import defaultdict
from collections import Counter
from typing import Dict, Generator, List, Union


import sys

sys.path.append('/data/republic/site-packages')

import pagexml.model.physical_document_model as pdm
from elasticsearch.exceptions import ElasticsearchException
# from elasticsearch.exceptions import TransportError
from fuzzy_search.search.phrase_searcher import FuzzyPhraseSearcher
# import pagexml.parser as pagexml_parser

from republic.helper.utils import get_commit_version

import republic.download.republic_data_downloader as downloader
import republic.elastic.republic_elasticsearch as republic_elasticsearch
import republic.extraction.extract_resolution_metadata as extract_res
import republic.helper.pagexml_helper as pagexml_helper
import republic.model.republic_document_model as rdm
import republic.model.resolution_phrase_model as rpm
from republic.classification.line_classification import NeuralLineClassifier
from republic.helper.metadata_helper import get_per_page_type_index, map_text_page_nums
from republic.helper.model_loader import load_line_break_detector
from republic.helper.pagexml_helper import json_to_pagexml_page
from republic.helper.utils import get_project_dir
from republic.model.inventory_mapping import get_inventories_by_year, get_inventory_by_num
from republic.model.republic_text_annotation_model import make_session_text_version

import republic.parser.logical.printed_resolution_parser as printed_res_parser
import republic.parser.logical.handwritten_resolution_parser as hand_res_parser
import republic.parser.pagexml.republic_pagexml_parser as pagexml_parser
from republic.parser.logical.generic_session_parser import make_session
from republic.parser.logical.handwritten_session_parser import get_handwritten_sessions
from republic.parser.logical.handwritten_resolution_parser import make_opening_searcher
from republic.parser.logical.printed_session_parser import get_printed_sessions

# logging.config.dictConfig({
#     'version': 1,
#     'disable_existing_loggers': True,
# })
logger = logging.getLogger(__name__)


def setup_logger(my_logger: logging.Logger, log_file: str, formatter: logging.Formatter,
                 level=logging.WARNING):
    """To setup as many loggers as you want.

    adapted from https://stackoverflow.com/questions/11232230/logging-to-two-files-with-different-settings
    """

    handler = logging.FileHandler(log_file)
    handler.setFormatter(formatter)

    my_logger.setLevel(level)
    my_logger.addHandler(handler)


def zip_exists(inv_num: int, ocr_type: str, base_dir: str):
    out_file = downloader.get_output_filename(inv_num, ocr_type, base_dir)
    if os.path.isfile(out_file):
        return True
    else:
        return False


def get_text_type(inv_num: int) -> str:
    return 'printed' if 400 <= inv_num <= 456 or 3760 <= inv_num <= 3864 else 'handwritten'


def get_page_content_type(page: pdm.PageXMLPage) -> str:
    # default_types = ['structure_doc', 'physical_structure_doc', 'text_region', 'pagexml_doc', 'page']
    content_types = ['resolution_page', 'index_page', 'respect_page']
    page_content_types = [pt for pt in page.metadata['type'] if pt in content_types]
    if len(page_content_types) > 1:
        raise TypeError(f"page {page.id} has multiple content types: {page_content_types}")
    elif len(page_content_types) == 0:
        return 'unknown'
    else:
        return page_content_types[0]


def filter_pages(pages: List[pdm.PageXMLPage], page_type: str):
    if len(pages) == 0:
        return pages
    inv_meta = get_inventory_by_num(pages[0].metadata['inventory_num'])
    content_types = [get_page_content_type(page) for page in pages]
    content_type_freq = Counter(content_types)
    for section in inv_meta['sections']:
        if section['page_type'] != page_type:
            continue
        if section['page_type'] not in content_type_freq:
            print(f"do_indexing.filter_pages - content_type_freq: {content_type_freq}")
            raise TypeError(f"do_indexing.filter_pages - no pages of type {section['page_type']} for "
                            f"inventory {inv_meta['inventory_num']}")
    return [page for page in pages if page.has_type(page_type)]


def write_pages(pages_file: str, pages: List[pdm.PageXMLPage]):
    with gzip.open(pages_file, 'wt') as fh:
        for page in pages:
            page_string = json.dumps(page.json)
            fh.write(f"{page_string}\n")


def get_last_pages(inv_num: int, indexer: Indexer):
    raw_pages_file = f"{indexer.base_dir}/pages/page_json/pages-{inv_num}.jsonl.gz"
    preprocessed_pages_file = f"{indexer.base_dir}/pages/preprocessed_page_json/preprocessed_pages-{inv_num}.jsonl.gz"
    pages_file = preprocessed_pages_file
    if os.path.exists(preprocessed_pages_file):
        if os.path.exists(raw_pages_file):
            # compare timestamps, take latest
            prep_stat = os.stat(preprocessed_pages_file)
            raw_stat = os.stat(raw_pages_file)
            pages_file = preprocessed_pages_file if prep_stat.st_mtime > raw_stat.st_mtime else raw_pages_file
        else:
            pages_file = preprocessed_pages_file
    elif os.path.exists(raw_pages_file):
        # create preprocessed pages file?
        pages_file = raw_pages_file
    page_state = 'preprocessed' if 'preprocessed' in pages_file else 'raw'
    if os.path.exists(pages_file):
        logger_string = f"Reading {page_state} pages from file for inventory {inv_num}"
        logger.info(logger_string)
        print(logger_string)
        pages = []
        with gzip.open(pages_file, 'rt') as fh:
            for line in fh:
                page_json = json.loads(line)
                page = json_to_pagexml_page(page_json)
                pages.append(page)
        return pages
    else:
        return None


def get_pages(inv_num: int, indexer: Indexer, page_type: str = None) -> List[pdm.PageXMLPage]:
    if os.path.exists(f"{indexer.base_dir}/pages") is False:
        os.mkdir(f"{indexer.base_dir}/pages")
    pages = get_last_pages(inv_num, indexer)
    """
    pages_file = f"{indexer.base_dir}/pages/page_json/pages-{inv_num}.jsonl.gz"
    if os.path.exists(pages_file):
        logger_string = f"Reading pages from file for inventory {inv_num}"
        logger.info(logger_string)
        print(logger_string)
        with gzip.open(pages_file, 'rt') as fh:
            pages = []
            for line in fh:
                page_json = json.loads(line)
                page = json_to_pagexml_page(page_json)
                pages.append(page)
    """
    if pages is None:
        logger_string = f"Downloading pages from ES index for inventory {inv_num}"
        logger.info(logger_string)
        print(logger_string)
        pages_file = f"{indexer.base_dir}/pages/page_json/pages-{inv_num}.jsonl.gz"
        pages = [page for page in indexer.rep_es.retrieve_inventory_pages(inv_num)]
        with gzip.open(pages_file, 'wt') as fh:
            for page in pages:
                page_string = json.dumps(page.json)
                fh.write(f"{page_string}\n")
    if page_type is not None:
        pages = filter_pages(pages, page_type)
    return pages


def get_session_starts(inv_id: str):
    project_dir = get_project_dir()
    print(f"do_indexing.get_session_starts - project_dir: {project_dir}")
    session_starts_file = os.path.join(project_dir, f"ground_truth/sessions/session_starts-{inv_id}.json")
    print(f"do_indexing.get_session_starts - session_starts_file: {session_starts_file}")

    if os.path.exists(session_starts_file):
        with open(session_starts_file, 'rt') as fh:
            return json.load(fh)
    else:
        return None


class Indexer:

    def __init__(self, host_type: str, base_dir: str = 'data'):
        self.host_type = host_type
        self.base_dir = base_dir
        self.sessions_json_dir = f'{base_dir}/sessions/sessions_json'
        if os.path.exists(f'{base_dir}/sessions') is False:
            os.mkdir(f'{base_dir}/sessions')
        if os.path.exists(self.sessions_json_dir) is False:
            os.mkdir(f'{base_dir}/sessions/sessions_json')
        self.rep_es = republic_elasticsearch.initialize_es(host_type=host_type, timeout=60)

    def set_indexes(self, indexing_step: str, indexing_label: str, debug: int = 0):
        if debug > 0:
            print(f'Indexer.set_indexes - indexing_step: {indexing_step}')
            print(f'Indexer.set_indexes - indexing_label: {indexing_label}')
        if indexing_step in {'resolution_metadata', 'attendance_list_spans'} and indexing_label is not None:
            self.rep_es.config['resolutions_index'] = f"{self.rep_es.config['resolutions_index']}_{indexing_label}"
            if debug > 0:
                print(f"Indexer.set_indexes - setting resolutions_index index "
                      f"name to {self.rep_es.config['resolutions_index']}")
            return None
        elif indexing_step == 'full_resolutions' and indexing_label is None:
            self.rep_es.config['resolutions_index'] = 'full_resolutions'
            if debug > 0:
                print(f"Indexer.set_indexes - setting resolutions_index index "
                      f"name to {self.rep_es.config['resolutions_index']}")
        if indexing_label is None:
            if debug > 0:
                print(f'Indexer.set_indexes - indexing_label is None: {indexing_label}')
            return None
        for key in self.rep_es.config:
            if key.startswith("session") and key.endswith("_index"):
                self.rep_es.config[key] = f"{self.rep_es.config[key]}_{indexing_label}"
                if debug > 0:
                    print(f'Indexer.set_indexes - setting {key} index name to {self.rep_es.config[key]}')
            elif key.startswith(indexing_step) and key.endswith("_index"):
                self.rep_es.config[key] = f"{self.rep_es.config[key]}_{indexing_label}"
                if debug > 0:
                    print(f'Indexer.set_indexes - setting {key} index name to {self.rep_es.config[key]}')

    def has_sections(self, inv_num: int):
        inv_metadata = self.rep_es.retrieve_inventory_metadata(inv_num)
        return "sections" in inv_metadata

    def index_session_resolutions(self, session: rdm.Session,
                                  opening_searcher: FuzzyPhraseSearcher,
                                  verb_searcher: FuzzyPhraseSearcher) -> None:
        for resolution in printed_res_parser.get_session_resolutions(session, opening_searcher, verb_searcher):
            self.rep_es.index_resolution(resolution)

    def do_downloading(self, inv_num: int, year_start: int, year_end: int):
        logger.info(f"Downloading pagexml zip file for inventory {inv_num} (years {year_start}-{year_end})...")
        print(f"Downloading pagexml zip file for inventory {inv_num} (years {year_start}-{year_end})...")
        ocr_type = "pagexml"
        downloader.download_inventory(inv_num, ocr_type, self.base_dir)

    def do_scan_indexing_pagexml(self, inv_num: int, year_start: int, year_end: int):
        logger.info(f"Indexing pagexml scans for inventory {inv_num} (years {year_start}-{year_end})...")
        print(f"Indexing pagexml scans for inventory {inv_num} (years {year_start}-{year_end})...")
        for si, scan in enumerate(self.rep_es.retrieve_text_repo_scans_by_inventory(inv_num)):
            try:
                logger.info('do_scan_indexing_pagexml - indexing scan', scan.id)
                print('do_scan_indexing_pagexml - indexing scan', scan.id)
                self.rep_es.index_scan(scan)
            except ZeroDivisionError:
                logger.error("ZeroDivisionError for scan", scan.id)
                print("ZeroDivisionError for scan", scan.id)

    def do_page_indexing_pagexml(self, inv_num: int, year_start: int, year_end: int):
        logger.info(f"Indexing pagexml pages for inventory {inv_num} (years {year_start}-{year_end})...")
        print(f"Indexing pagexml pages for inventory {inv_num} (years {year_start}-{year_end})...")
        try:
            inv_metadata = self.rep_es.retrieve_inventory_metadata(inv_num)
        except ValueError:
            logger.info(f"Skipping page indexing for inventory {inv_num} (years {year_start}-{year_end})...")
            print(f"Skipping page indexing for inventory {inv_num} (years {year_start}-{year_end})...")
            return None
        page_type_index = get_per_page_type_index(inv_metadata)
        text_page_num_map = map_text_page_nums(inv_metadata)
        page_count = 0
        num_scans = inv_metadata['num_scans']
        nlc_gysbert = None
        if inv_num < 3760 or inv_num > 3864:
            model_dir = 'data/models/neural_line_classification/nlc_gysbert_model'
            nlc_gysbert = NeuralLineClassifier(model_dir)
        for si, scan in enumerate(self.rep_es.retrieve_inventory_scans(inv_num)):
            try:
                pages = pagexml_parser.split_pagexml_scan(scan, page_type_index, debug=0)
            except Exception as err:
                logger.error(err)
                logger.info('Error splitting pages of scan', scan.id)
                print('Error splitting pages of scan', scan.id)
                raise
            for page in pages:
                page_count += 1
                if page.metadata['page_num'] in text_page_num_map:
                    page_num = page.metadata['page_num']
                    page.metadata['text_page_num'] = text_page_num_map[page_num]['text_page_num']
                    page.metadata['skip'] = text_page_num_map[page_num]['skip']
                    if text_page_num_map[page_num]['problem'] is not None:
                        page.metadata['problem'] = text_page_num_map[page_num]['problem']
                if page_type_index is None:
                    page.add_type('unknown')
                    page.metadata['type'] = [ptype for ptype in page.type]
                elif page.metadata['page_num'] not in page_type_index:
                    page.add_type("empty_page")
                    page.metadata['type'] = [ptype for ptype in page.type]
                    page.metadata['skip'] = True
                    # print("page without page_num:", page.id)
                    # print("\tpage stats:", page.stats)
                else:
                    page_types = page_type_index[page.metadata['page_num']]
                    if isinstance(page_types, str):
                        page_types = [page_types]
                    for page_type in page_types:
                        page.add_type(page_type)
                    page.metadata['type'] = [ptype for ptype in page.type]
                predicted_line_class = nlc_gysbert.classify_page_lines(page) if nlc_gysbert else {}
                for tr in page.get_all_text_regions():
                    for line in tr.lines:
                        line.metadata['text_region_id'] = tr.id
                        if line.id in predicted_line_class:
                            line.metadata['line_class'] = predicted_line_class[line.id]
                        else:
                            line.metadata['line_class'] = 'unknown'
                logger.info(f'indexing page {page_count} (scan count {si+1} of {num_scans}) with id {page.id}')
                print(f'indexing page {page_count} (scan count {si+1} of {num_scans}) with id {page.id}')
                prov_url = self.rep_es.post_provenance([scan.id], [page.id], 'scans', 'pages')
                page.metadata['provenance_url'] = prov_url
                self.rep_es.index_page(page)
            if (si+1) % 100 == 0:
                logger.info(si+1, "scans processed")
                print(si+1, "scans processed")

    def do_page_type_indexing_pagexml(self, inv_num: int, year_start: int, year_end: int):
        logger.info(f"Updating page types for inventory {inv_num} (years {year_start}-{year_end})...")
        print(f"Updating page types for inventory {inv_num} (years {year_start}-{year_end})...")
        inv_metadata = self.rep_es.retrieve_inventory_metadata(inv_num)
        pages = self.rep_es.retrieve_inventory_pages(inv_num)
        self.rep_es.add_pagexml_page_types(inv_metadata, pages)
        resolution_page_offset = 0
        for offset in inv_metadata["type_page_num_offsets"]:
            if offset["page_type"] == "resolution_page":
                resolution_page_offset = offset["page_num_offset"]
        # print(inv_num, "resolution_page_offset:", resolution_page_offset)
        pages = self.rep_es.retrieve_inventory_resolution_pages(inv_num)
        for page in sorted(pages, key=lambda x: x["metadata"]["page_num"]):
            type_page_num = page.metadata["page_num"] - resolution_page_offset + 1
            if type_page_num <= 0:
                page.metadata["page_type"].remove("resolution_page")
            else:
                page.metadata["type_page_num"] = type_page_num
            self.rep_es.index_page(page)

    def download_pages(self, inv_num: int, year_start: int, year_end: int):
        logger_string = f"Downloading PageXML pages for " \
                        f"inventory {inv_num} (years {year_start}-{year_end})..."
        logger.info(logger_string)
        print(f"Getting PageXML sessions from pages for inventory {inv_num} (years {year_start}-{year_end})...")
        get_pages(inv_num, self)

    def get_sessions_from_pages(self, inv_num: int, year_start: int, year_end: int, from_starts: bool = False):
        logger_string = f"Getting PageXML sessions from pages for inventory {inv_num} " \
                        f"(years {year_start}-{year_end})..."
        logger.info(logger_string)
        print(f"Getting PageXML sessions from pages for inventory {inv_num} (years {year_start}-{year_end})...")

        inv_metadata = get_inventory_by_num(inv_num)
        inv_id = inv_metadata['inventory_id']
        text_type = get_text_type(inv_num)
        if from_starts is True:
            session_starts = get_session_starts(inv_id)
            if session_starts is None:
                logger.warning(f"WARNING - No sessions starts for inventory {inv_num}")
                print(f"WARNING - No sessions starts for inventory {inv_num}")
                return None
        else:
            session_starts = None

        pages = get_pages(inv_num, self, page_type='resolution_page')
        pages.sort(key=lambda page: page.metadata['page_num'])
        print(f'inventory {inv_num} - number of pages: {len(pages)}')
        pages = [page for page in pages if "skip" not in page.metadata or page.metadata["skip"] is False]
        print(f'inventory {inv_num} - number of non-skipped pages: {len(pages)}')

        get_session_func = get_printed_sessions if text_type == 'printed' else get_handwritten_sessions
        # use_token_searcher = True if text_type == 'printed' else False
        # include_variants not yet implemented in FuzzyTokenSearcher so use FuzzyPhraseSearcher
        use_token_searcher = False
        prev_session = None
        try:
            for session in get_session_func(inv_metadata['inventory_id'], pages,
                                            session_starts=session_starts,
                                            use_token_searcher=use_token_searcher, debug=1):
                yield session
                prev_session = session
        except Exception as err:
            logger_string = f'last successful session: {prev_session.id}'
            logger.info(logger_string)
            logger.info(prev_session.stats)
            logger.info(err)
            print(f"Error getting {text_type} {inv_num} session after {prev_session.id}")
            raise

    def write_sessions_to_files(self, inv_num: int, year_start: int, year_end: int):
        logger_string = f"Writing PageXML sessions for inventory {inv_num} (years {year_start}-{year_end})..."
        logger.info(logger_string)
        print(f"Writing PageXML sessions for inventory {inv_num} (years {year_start}-{year_end})...")
        session_inv_dir = f'{self.sessions_json_dir}/{inv_num}'
        if os.path.exists(session_inv_dir) is False:
            os.mkdir(session_inv_dir)
        for mi, session in enumerate(self.get_sessions_from_pages(inv_num, year_start, year_end)):
            logger_string = 'session received from get_sessions:', session.id
            logger.info(logger_string)
            print('session received from get_sessions:', session.id)
            date_string = None
            for match in session.evidence:
                if match.has_label('session_date'):
                    date_string = match.string
            logger_string = f'\tdate string: {date_string}'
            logger.info(logger_string)
            print('\tdate string:', date_string)
            json_file = os.path.join(session_inv_dir, f"session-{session.date.isoformat()}.json.gz")
            with gzip.open(json_file, 'wt') as fh:
                json.dump(session.json, fh)

    def get_sessions_from_files(self, inv_num: int, year_start: int, year_end: int):
        logger.info(f"Getting PageXML sessions from pages for inventory {inv_num} (years {year_start}-{year_end})...")
        print(f"Getting PageXML sessions from pages for inventory {inv_num} (years {year_start}-{year_end})...")
        session_inv_dir = f'{self.sessions_json_dir}/{inv_num}'
        if os.path.exists(session_inv_dir) is False:
            return None
        session_files = glob.glob(os.path.join(session_inv_dir, 'session-*.json.gz'))
        for session_file in sorted(session_files):
            with gzip.open(session_file, 'rt') as fh:
                session = json.load(fh)
                yield rdm.json_to_republic_session(session)

    def do_session_lines_indexing(self, inv_num: int, year_start: int, year_end: int):
        logger.info(f"Indexing PageXML sessions for inventory {inv_num} (years {year_start}-{year_end})...")
        print(f"Indexing PageXML sessions for inventory {inv_num} (years {year_start}-{year_end})...")
        inv_metadata = self.rep_es.retrieve_inventory_metadata(inv_num)
        if "period_start" not in inv_metadata:
            return None
        for session in self.get_sessions_from_files(inv_num, year_start, year_end):
            source_ids = session.metadata['page_ids']
            try:
                prov_url = self.rep_es.post_provenance(source_ids=source_ids, target_ids=[session.id],
                                                       source_index='pages', target_index='session_lines')
                session.metadata['prov_url'] = prov_url
                logger.info('indexing session from files', session.id)
                print('indexing session from files', session.id)
                self.rep_es.index_session_with_lines(session)
            except ElasticsearchException as error:
                logger.info(session.id)
                logger.info(session.stats)
                logger.info(error)
                print(f"Error indexing session_with_lines {session.id}")
                continue

    def do_session_text_indexing(self, inv_num: int, year_start: int, year_end: int):
        logger.info(f"Indexing PageXML sessions for inventory {inv_num} (years {year_start}-{year_end})...")
        print(f"Indexing PageXML sessions for inventory {inv_num} (years {year_start}-{year_end})...")
        for mi, session in enumerate(self.rep_es.retrieve_inventory_sessions_with_lines(inv_num)):
            logger.info('indexing session text for session', session.id)
            print('indexing session text for session', session.id)
            resolutions = self.rep_es.retrieve_resolutions_by_session_id(session.id)
            # for res in resolutions:
            #     print(res.id, res.metadata['type'])
            session_text_doc = make_session_text_version(session, resolutions)
            self.rep_es.index_session_with_text(session_text_doc)

    def do_session_indexing(self, inv_num: int, year_start: int, year_end: int, from_files: bool = False,
                            from_starts: bool = False):
        logger.info(f"Indexing PageXML sessions for inventory {inv_num} (years {year_start}-{year_end})...")
        print(f"Indexing PageXML sessions for inventory {inv_num} (years {year_start}-{year_end})...")
        inv_metadata = get_inventory_by_num(inv_num)
        text_type = get_text_type(inv_num)
        errors = []
        if from_files is True:
            get_session_gen = self.get_sessions_from_files(inv_num, year_start, year_end)
        else:
            get_session_gen = self.get_sessions_from_pages(inv_num, year_start, year_end, from_starts=from_starts)
        try:
            for session in get_session_gen:
                session_json = make_session(inv_metadata, session.date_metadata, session.metadata['session_num'],
                                            text_type, session.text_regions)
                logger.info(f'indexing {text_type} session {session.id} with date {session.date.isoformat()}')
                print(f'indexing {text_type} session {session.id} with date {session.date.isoformat()}')
                prov_url = self.rep_es.post_provenance(source_ids=session_json['page_ids'], target_ids=[session.id],
                                                       source_index='pages', target_index='session_metadata',
                                                       ignore_prov_errors=True)
                print(f'\tsession has {len(session.text_regions)} text regions')
                session_json['metadata']['prov_url'] = prov_url
                session.metadata['prov_url'] = prov_url
                self.rep_es.index_session_metadata(session_json)
                for tr in session.text_regions:
                    prov_url = self.rep_es.post_provenance(source_ids=[tr.metadata['page_id']], target_ids=[tr.id],
                                                           source_index='pages', target_index='session_text_region',
                                                           ignore_prov_errors=True)
                    tr.metadata['prov_url'] = prov_url
                self.rep_es.index_session_text_regions(session.text_regions)
        except Exception as err:
            logger.error(err)
            logger.error('ERROR PARSING SESSIONS FOR INV_NUM', inv_num)
            errors.append(err)
            print(err)
            print('ERROR PARSING SESSIONS FOR INV_NUM', inv_num)
            # raise
        error_label = f"{len(errors)} errors" if len(errors) > 0 else "no errors"
        logger.info(f"finished indexing sessions of inventory {inv_num} with {error_label}")
        print(f"finished indexing sessions of inventory {inv_num} with {error_label}")

    def get_inventory_sessions(self, inv_num: int) -> Generator[rdm.Session, None, None]:
        inv_session_metas = self.rep_es.retrieve_inventory_session_metadata(inv_num)
        inv_session_trs = defaultdict(list)
        for tr in self.rep_es.retrieve_inventory_session_text_regions(inv_num):
            if 'session_id' not in tr.metadata:
                continue
            inv_session_trs[tr.metadata['session_id']].append(tr)
        for session_meta in inv_session_metas:
            try:
                session_id = session_meta['id']
                if session_id not in inv_session_trs:
                    print(f're-indexing text regions for session {session_id}')
                    session_trs_json = self.rep_es.retrieve_session_trs_by_metadata(session_meta)
                    session_trs = [pagexml_helper.json_to_pagexml_text_region(tr_json) for tr_json in session_trs_json]
                    for tr in session_trs:
                        tr.metadata['inventory_num'] = session_meta['metadata']['inventory_num']
                        tr.metadata['session_id'] = session_id
                        for line in tr.lines:
                            line.metadata['inventory_num'] = session_meta['metadata']['inventory_num']
                    self.rep_es.index_bulk_docs('session_text_regions', [tr.json for tr in session_trs])
                    inv_session_trs[session_id] = session_trs
                session = rdm.Session(doc_id=session_meta['id'], session_data=session_meta,
                                      text_regions=inv_session_trs[session_meta['id']])
                yield session
            except (TypeError, KeyError) as err:
                logger.error(f"Error generation session {session_meta['id']} from metadata and text regions")
                logger.error(err)
                raise

    def do_printed_resolution_indexing(self, inv_num: int, year_start: int, year_end: int):
        logger.info(f"Indexing PageXML resolutions for inventory {inv_num} (years {year_start}-{year_end})...")
        print(f"Indexing PageXML resolutions for inventory {inv_num} (years {year_start}-{year_end})...")
        opening_searcher, verb_searcher = printed_res_parser.configure_resolution_searchers()
        line_break_detector = load_line_break_detector()
        self.rep_es.delete_by_inventory(inv_num, self.rep_es.config['resolutions_index'])
        errors = []
        for session in self.get_inventory_sessions(inv_num):
            logger.info(f"indexing resolutions for session {session.id}")
            print(f"indexing resolutions for session {session.id}")
            if "index_timestamp" not in session.metadata:
                self.rep_es.es_anno.delete(index="session_lines", id=session.id)
                logger.info("DELETING SESSION WITH ID", session.id)
                print("DELETING SESSION WITH ID", session.id)
                continue
            try:
                for resolution in printed_res_parser.get_session_resolutions(session, opening_searcher,
                                                                             verb_searcher,
                                                                             line_break_detector=line_break_detector):
                    try:
                        prov_url = self.rep_es.post_provenance(source_ids=[session.id], target_ids=[resolution.id],
                                                               source_index='session_lines', target_index='resolutions',
                                                               ignore_prov_errors=True)
                    except Exception as err:
                        logger.error(f'Error posting provenance for resolution {resolution.id}')
                        logger.error(err)
                        errors.append(err)
                        prov_url = None
                    resolution.metadata['prov_url'] = prov_url
                    logger.info(f"indexing resolution {resolution.id}")
                    self.rep_es.index_resolution(resolution)
            except (TypeError, KeyError) as err:
                errors.append(err)
                logging.error('Error parsing resolutions for inv_num', inv_num)
                logging.error(err)
                # pass
                raise
        error_label = f"{len(errors)} errors" if len(errors) > 0 else "no errors"
        logger.info(f"finished indexing printed resolutions of inventory {inv_num} with {error_label}")
        print(f"finished indexing printed resolutions of inventory {inv_num} with {error_label}")
        for err in errors:
            print(err)

    def do_handwritten_resolution_indexing(self, inv_num: int, year_start: int, year_end: int):
        logger.info(f"Indexing handwritten PageXML resolutions for inventory {inv_num} "
                    f"(years {year_start}-{year_end})...")
        print(f"Indexing handwritten PageXML resolutions for inventory {inv_num} (years {year_start}-{year_end})...")
        opening_searcher = make_opening_searcher(year_start, year_end, debug=0)
        errors = []
        for session in self.get_inventory_sessions(inv_num):
            try:
                # print('session_meta["id"]:', session_meta['id'])
                print('session.id:', session.id, '\tnum text_regions:', len(session.text_regions))
                for resolution in hand_res_parser.get_session_resolutions(session, opening_searcher, debug=1):
                    source_ids = [session.id] + [tr.id for tr in session.text_regions]
                    prov_url = self.rep_es.post_provenance(source_ids=source_ids,
                                                           target_ids=[resolution.id],
                                                           source_index='session_metadata', target_index='resolutions',
                                                           ignore_prov_errors=True)
                    resolution.metadata['prov_url'] = prov_url
                    self.rep_es.index_resolution(resolution)
                    print('indexing handwritten resolution', resolution.id)
                    # self.rep_es.es_anno.index(index=res_index, id=res.id, document=res.json)
            except Exception as err:
                print('ERROR PARSING RESOLUTIONS FOR INV_NUM', inv_num)
                logging.error('Error parsing resolutions for inv_num', inv_num)
                logging.error(err)
                print(err)
                errors.append(err)
                raise
        error_label = f"{len(errors)} errors" if len(errors) > 0 else "no errors"
        logger.info(f"finished indexing printed resolutions of inventory {inv_num} with {error_label}")
        print(f"finished indexing printed resolutions of inventory {inv_num} with {error_label}")
        for err in errors:
            print(err)

    def do_resolution_indexing(self, inv_num: int, year_start: int, year_end: int):
        self.rep_es.delete_by_inventory(inv_num, self.rep_es.config['resolutions_index'])
        if 3760 <= inv_num <= 3864 or 400 <= inv_num <= 456:
            self.do_printed_resolution_indexing(inv_num, year_start, year_end)
        else:
            self.do_handwritten_resolution_indexing(inv_num, year_start, year_end)

    def do_resolution_phrase_match_indexing(self, inv_num: int, year_start: int, year_end: int):
        logger.info(f"Indexing PageXML resolution phrase matches for inventory "
                    f"{inv_num} (years {year_start}-{year_end})...")
        print(f"Indexing PageXML resolution phrase matches for inventory {inv_num} (years {year_start}-{year_end})...")
        searcher = printed_res_parser.make_resolution_phrase_model_searcher()
        for resolution in self.rep_es.scroll_inventory_resolutions(inv_num):
            print('indexing phrase matches for resolution', resolution.metadata['id'])
            num_paras = len(resolution.paragraphs)
            num_matches = 0
            for paragraph in resolution.paragraphs:
                doc = {'id': paragraph.metadata['id'], 'text': paragraph.text}
                for match in searcher.find_matches(doc):
                    self.rep_es.index_resolution_phrase_match(match, resolution)
                    num_matches += 1
                    self.rep_es.index_resolution_phrase_match(match, resolution)
            print(f'\tparagraphs: {num_paras}\tnum matches: {num_matches}')

    def do_resolution_metadata_indexing(self, inv_num: int, year_start: int, year_end: int):
        logger.info(f"Indexing PageXML resolution metadata for inventory {inv_num} (years {year_start}-{year_end})...")
        print(f"Indexing PageXML resolution metadata for inventory {inv_num} (years {year_start}-{year_end})...")
        errors = []
        searcher = printed_res_parser.make_resolution_phrase_model_searcher()
        relative_path = rpm.__file__.split("republic-project/")[-1]
        repo_url = 'https://github.com/HuygensING/republic-project'
        phrase_file = f'{repo_url}/blob/{get_commit_version()}/{relative_path}'
        prop_searchers = extract_res.generate_proposition_searchers()
        for resolution in self.rep_es.scroll_inventory_resolutions(inv_num):
            try:
                phrase_matches = extract_res.extract_paragraph_phrase_matches(resolution.paragraphs[0],
                                                                              [searcher])
                new_resolution = extract_res.add_resolution_metadata(resolution, phrase_matches,
                                                                     prop_searchers['template'],
                                                                     prop_searchers['variable'])
                prov_url = self.rep_es.post_provenance(source_ids=[resolution.id], target_ids=[resolution.id],
                                                       source_index='resolutions', target_index='resolutions',
                                                       source_external_urls=[phrase_file],
                                                       why='Enriching resolution with metadata derived from '
                                                           'resolution phrases')
                if 'prov_url' not in new_resolution.metadata or new_resolution.metadata['prov_url'] is None:
                    new_resolution.metadata['prov_url'] = [prov_url]
                if isinstance(new_resolution.metadata['prov_url'], str):
                    new_resolution.metadata['prov_url'] = [new_resolution.metadata['prov_url']]
                if prov_url not in new_resolution.metadata['prov_url']:
                    new_resolution.metadata['prov_url'].append(prov_url)
                logger.info('\tadding resolution metadata for resolution', new_resolution.id)
                print('\tadding resolution metadata for resolution', new_resolution.id)
                self.rep_es.index_resolution(new_resolution)
            except Exception as err:
                errors.append(err)
                logger.error(err)
                logger.error(f'ERROR - do_resolution_metadata_indexing - resolution.id: {resolution.id}')
                print(f'ERROR - do_resolution_metadata_indexing - resolution.id: {resolution.id}')
                pass
                # raise
        error_label = f"{len(errors)} errors" if len(errors) > 0 else "no errors"
        logger.info(f"finished indexing resolution metadata of inventory {inv_num} with {error_label}")
        print(f"finished indexing resolution metadata of inventory {inv_num} with {error_label}")

    def do_resolution_metadata_indexing_old(self, inv_num: int, year_start: int, year_end: int):
        logger.info(f"Indexing PageXML resolution metadata for inventory {inv_num} (years {year_start}-{year_end})...")
        print(f"Indexing PageXML resolution metadata for inventory {inv_num} (years {year_start}-{year_end})...")
        prop_searchers = extract_res.generate_proposition_searchers()
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
        for ri, resolution in enumerate(self.rep_es.scroll_inventory_resolutions(inv_num)):
            if resolution.metadata['type'] == 'attendance_list':
                attendance += 1
                continue
            if len(resolution.evidence) == 0:
                logger.info('resolution without evidence:', resolution.metadata)
                print('resolution without evidence:', resolution.metadata)
            if resolution.evidence[0].phrase.phrase_string in skip_formulas:
                logger.info('skip formula:', resolution.id)
                print('skip formula:', resolution.id)
                # print(resolution.paragraphs[0].text)
                # print(resolution.evidence[0])
                # print()
                # continue
            phrase_matches = extract_res.get_paragraph_phrase_matches(self.rep_es, resolution)
            new_resolution = extract_res.add_resolution_metadata(resolution, phrase_matches,
                                                                 prop_searchers['template'],
                                                                 prop_searchers['variable'])
            if not new_resolution:
                no_new += 1
                continue
            # print(new_resolution.metadata)
            if (ri+1) % 100 == 0:
                logger.info(ri+1, 'resolutions parsed\t', attendance, 'attendance lists\t', no_new, 'non-metadata')
                print(ri+1, 'resolutions parsed\t', attendance, 'attendance lists\t', no_new, 'non-metadata')
            try:
                self.rep_es.index_resolution_metadata(new_resolution)
                self.rep_es.index_resolution(new_resolution)
            except Exception as err:
                logger.error(err)
                logger.error('issue with resolution metadata:\n', json.dumps(new_resolution.metadata, indent=4))
                print('issue with resolution metadata:\n', json.dumps(new_resolution.metadata, indent=4))
                raise

    def do_inventory_attendance_list_indexing(self, inv_num: int, year_start: int, year_end: int):
        logger.info(f"Indexing attendance lists with spans for inventory {inv_num} (years {year_start}-{year_end})...")
        print(f"Indexing attendance lists with spans for inventory {inv_num} (years {year_start}-{year_end})...")
        errors = []
        # print('do_inventory_attendance_list_indexing - index:', self.rep_es.config['resolutions_index'])
        import run_attendancelist
        for year in range(year_start, year_end + 1):
            try:
                att_spans_year = run_attendancelist.run(self.rep_es.es_anno, year, outdir=None,
                                                        verbose=True, tofile=False,
                                                        source_index=self.rep_es.config['resolutions_index'])
                if att_spans_year is None:
                    return None
                for span_list in att_spans_year:
                    # print(span_list['metadata']['zittingsdag_id'])
                    # print(span_list['spans'])
                    att_id = f'{span_list["metadata"]["zittingsdag_id"]}-attendance_list'
                    att_list = self.rep_es.retrieve_attendance_list_by_id(att_id)
                    att_list.attendance_spans = span_list["spans"]
                    print(f"re-indexing attendance list {att_list.id} with {len(span_list['spans'])} spans")
                    self.rep_es.index_attendance_list(att_list)
            except Exception as err:
                errors.append(err)
                logger.error(err)
                logger.error(f'Error - issue with attendance lists for year {year}')
                print(f'Error - issue with attendance lists for year {year}')
                raise
        error_label = f"{len(errors)} errors" if len(errors) > 0 else "no errors"
        logger.info(f"finished indexing attendance lists of inventory {inv_num} with {error_label}")
        print(f"finished indexing attendance lists of inventory {inv_num} with {error_label}")


def process_inventory(task: Dict[str, Union[str, int]]):
    log_file = f"indexing-{task['indexing_step']}-date-{datetime.date.today().isoformat()}.log"
    formatter = logging.Formatter('%(asctime)s\t%(levelname)s\t%(message)s')
    setup_logger(logger, log_file, formatter, level=logging.DEBUG)
    indexer = Indexer(task["host_type"], base_dir=task["base_dir"])
    print("TASK:", task)
    indexer.set_indexes(task["indexing_step"], task["index_label"])
    # print('process_inventory - index:', indexer.rep_es.config['resolutions_index'])
    if task["indexing_step"] == "download":
        indexer.do_downloading(task["inv_num"], task["year_start"], task["year_end"])
    elif task["indexing_step"] == "download_pages":
        indexer.download_pages(task["inv_num"], task["year_start"], task["year_end"])
    elif task["indexing_step"] == "scans_pages":
        indexer.do_scan_indexing_pagexml(task["inv_num"], task["year_start"], task["year_end"])
        indexer.do_page_indexing_pagexml(task["inv_num"], task["year_start"], task["year_end"])
    elif task["indexing_step"] == "scans":
        indexer.do_scan_indexing_pagexml(task["inv_num"], task["year_start"], task["year_end"])
    elif task["indexing_step"] == "pages":
        indexer.do_page_indexing_pagexml(task["inv_num"], task["year_start"], task["year_end"])
    elif task["indexing_step"] == "page_types":
        indexer.do_page_type_indexing_pagexml(task["inv_num"], task["year_start"], task["year_end"])
    elif task["indexing_step"] == "session_files":
        indexer.get_sessions_from_pages(task["inv_num"], task["year_start"], task["year_end"])
    elif task["indexing_step"] == "session_lines":
        indexer.do_session_lines_indexing(task["inv_num"], task["year_start"], task["year_end"])
    elif task["indexing_step"] == "session_text":
        indexer.do_session_text_indexing(task["inv_num"], task["year_start"], task["year_end"])
    elif task["indexing_step"] == "sessions_write":
        indexer.write_sessions_to_files(task["inv_num"], task["year_start"], task["year_end"])
    elif task["indexing_step"] == "sessions_indexing_from_files":
        indexer.do_session_indexing(task["inv_num"], task["year_start"], task["year_end"], from_files=True)
    elif task["indexing_step"] == "sessions_indexing_from_pages":
        indexer.do_session_indexing(task["inv_num"], task["year_start"], task["year_end"], from_files=False,
                                    from_starts=False)
    elif task["indexing_step"] == "sessions_indexing_from_starts":
        indexer.do_session_indexing(task["inv_num"], task["year_start"], task["year_end"], from_files=False,
                                    from_starts=True)
    elif task["indexing_step"] == "resolutions":
        indexer.do_resolution_indexing(task["inv_num"], task["year_start"], task["year_end"])
    elif task["indexing_step"] == "handwritten_resolutions":
        indexer.rep_es.config['resolutions_index'] = 'handwritten_resolutions'
        indexer.do_resolution_indexing(task["inv_num"], task["year_start"], task["year_end"])
    elif task["indexing_step"] == "full_resolutions":
        # indexer.rep_es.config['resolutions_index'] = 'full_resolutions'
        indexer.do_resolution_indexing(task["inv_num"], task["year_start"], task["year_end"])
        indexer.do_resolution_metadata_indexing(task["inv_num"], task["year_start"], task["year_end"])
        indexer.do_inventory_attendance_list_indexing(task["inv_num"], task["year_start"], task["year_end"])
    elif task["indexing_step"] == "phrase_matches":
        indexer.do_resolution_phrase_match_indexing(task["inv_num"], task["year_start"], task["year_end"])
    elif task["indexing_step"] == "resolution_metadata":
        # indexer.rep_es.config['resolutions_index'] = 'full_resolutions'
        indexer.do_resolution_metadata_indexing(task["inv_num"], task["year_start"], task["year_end"])
    elif task["indexing_step"] == "attendance_list_spans":
        # indexer.rep_es.config['resolutions_index'] = 'full_resolutions'
        indexer.do_inventory_attendance_list_indexing(task["inv_num"], task["year_start"], task["year_end"])
    else:
        raise ValueError(f'Unknown task type {task["indexing_step"]}')
    print(f"Finished indexing {task['indexing_step']} for inventory {task['inv_num']}, "
          f"years {task['year_start']}-{task['year_end']}")


def parse_args():
    argv = sys.argv[1:]
    # Define the getopt parameters
    try:
        opts, args = getopt.getopt(argv, 's:e:i:n:l:b:', ['foperand', 'soperand'])
        start, end, indexing_step, num_processes, index_label = None, None, None, None, None
        base_dir = 'data'
        for opt, arg in opts:
            if opt == '-n':
                num_processes = int(arg)
            if opt == '-s':
                start = int(arg)
            if opt == '-e':
                end = int(arg)
            if opt == '-i':
                indexing_step = arg
            if opt == '-l':
                index_label = arg
            if opt == '-b':
                base_dir = arg
        print(start, end, indexing_step, num_processes)
        if not start or not end or not indexing_step or not num_processes:
            print('usage: do_indexing.py -s <start_year> -e <end_year> -i <indexing_step> '
                  '-n <num_processes> -l <label_index_name> -b <base_dir>')
            sys.exit(2)
        indexing_steps = indexing_step.split(';')
        return start, end, indexing_steps, num_processes, index_label, base_dir
    except getopt.GetoptError as err:
        # Print something useful
        print('usage: do_indexing.py -s <start_year> -e <end_year> -i <indexing_step> -n <num_processes> '
              '(optional) -l <index_label> -b <base_dir>')
        print(err)
        sys.exit(2)


def get_tasks(start, end, indexing_step, index_label: str, host_type: str, base_dir: str) -> List[Dict[str, any]]:
    # Get the Git repository commit hash for keeping provenance
    commit_version = get_commit_version()

    if start in range(1576, 1797):

        tasks = []
        years = [year for year in range(start, end+1)]
        for year in years:
            for inv_map in get_inventories_by_year(year):
                task: Dict[str, any] = {
                    'year_start': inv_map['year_start'],
                    'year_end': inv_map['year_end'],
                    'indexing_step': indexing_step,
                    'index_label': index_label,
                    'host_type': host_type,
                    'base_dir': base_dir,
                    'commit': commit_version,
                    'inv_num': inv_map['inventory_num']
                }
                tasks.append(task)
        print(f'indexing {indexing_step} for years', years)
    elif start in range(3000, 5000):
        inv_nums = [inv_num for inv_num in range(start, end+1)]
        tasks = []
        for inv_num in range(start, end + 1):
            task = {
                "inv_num": inv_num,
                "indexing_step": indexing_step,
                'index_label': index_label,
                'host_type': host_type,
                'base_dir': base_dir,
                "commit": commit_version
            }
            tasks.append(task)

        for task in tasks:
            inv_map = get_inventory_by_num(task["inv_num"])
            if inv_map is None:
                print('No inventory metadata for inventory number', task['inv_num'])
                continue
            task["year_start"] = inv_map["year_start"]
            task["year_end"] = inv_map["year_end"]
        tasks = [task for task in tasks if 'year_start' in task and task['year_start'] is not None]
        print(f'indexing {indexing_step} for inventories', inv_nums)
    else:
        raise ValueError("Unknown start number, expecting 1576-1796 or 3760-3864")
    return tasks


def main():
    host_type = os.environ.get('REPUBLIC_HOST_TYPE')
    if not host_type:
        host_type = "external"
    # Get the arguments from the command-line except the filename
    start, end, indexing_steps, num_processes, index_label, base_dir = parse_args()
    # logging.basicConfig(filename=log_file, encoding='utf-8',
    #                     format='%(asctime)s\t%(levelname)s\t%(message)s', level=logging.DEBUG)

    for indexing_step in indexing_steps:
        tasks = get_tasks(start, end, indexing_step, index_label, host_type, base_dir)
        if 'session' in indexing_step or 'resolution' in indexing_step and index_label is None:
            index_label = "staging"
        if num_processes > 1:
            with multiprocessing.Pool(processes=num_processes) as pool:
                # use a chunksize of 1 to ensure inventories are processed more or less in order.
                pool.map(process_inventory, tasks, 1)
        else:
            for task in tasks:
                process_inventory(task)
        if indexing_step == "session_lines":
            for task in tasks:
                indexer = Indexer(host_type, base_dir)
                indexer.do_session_lines_indexing(task["inv_num"], task["year_start"], task["year_end"])


if __name__ == "__main__":
    import getopt
    import sys

    main()
