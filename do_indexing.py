from __future__ import annotations
import datetime
import glob
import gzip
import json
import logging
import logging.config
import multiprocessing
import os
import re
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
from republic.helper.utils import make_index_urls
import republic.model.republic_document_model as rdm
import republic.model.resolution_phrase_model as rpm
from republic.analyser.quality_control import check_element_types
from republic.classification.line_classification import NeuralLineClassifier
from republic.classification.content_classification import get_header_dates
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
from republic.parser.logical.generic_session_parser import make_session_from_meta_and_trs
from republic.parser.logical.handwritten_session_parser import get_handwritten_sessions
from republic.parser.logical.handwritten_resolution_parser import make_opening_searcher
from republic.parser.logical.printed_session_parser import get_printed_sessions
from republic.parser.pagexml.page_date_parser import process_handwritten_pages
from republic.parser.pagexml.page_date_parser import classify_page_date_regions
from republic.parser.pagexml.page_date_parser import load_date_region_classifier

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
    if 400 <= inv_num <= 456:
        return 'handgeschreven' if inv_num in [401, 429, 430, 432, 433, 436, 437] else 'gedrukt'
    else:
        return 'gedrukt' if 3760 <= inv_num <= 3864 else 'handgeschreven'


def get_page_content_type(page: pdm.PageXMLPage) -> str:
    # default_types = ['structure_doc', 'physical_structure_doc', 'text_region', 'pagexml_doc', 'page']
    content_types = ['resolution_page', 'index_page', 'respect_page']
    page_content_types = [pt for pt in page.type if pt in content_types]
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


def make_page_generator(inv_num: int, pages_file: str, page_state: str = None):
    if os.path.exists(pages_file) is False:
        return None
    page_string = "pages" if page_state is None else f"{page_state} pages"
    logger_string = f"Reading {page_string} from file for inventory {inv_num}"
    logger.info(logger_string)
    print(logger_string)
    with gzip.open(pages_file, 'rt') as fh:
        for line in fh:
            page_json = json.loads(line)
            page = json_to_pagexml_page(page_json)
            check_line_metadata([page])
            yield page


def get_raw_pages(inv_num: int, indexer: Indexer):
    raw_pages_file = f"{indexer.base_dir}/pages/raw_page_json/raw_pages-{inv_num}.jsonl.gz"
    print('raw_pages_file:', raw_pages_file)
    return make_page_generator(inv_num, raw_pages_file, 'raw')


def get_preprocessed_pages(inv_num: int, indexer: Indexer):
    preprocessed_pages_file = f"{indexer.base_dir}/pages/preprocessed_page_json/preprocessed_pages-{inv_num}.jsonl.gz"
    print('preprocessed_pages_file:', preprocessed_pages_file)
    return make_page_generator(inv_num, preprocessed_pages_file, 'preprocessed')


def get_last_pages(inv_num: int, indexer: Indexer):
    raw_pages_file = f"{indexer.base_dir}/pages/raw_page_json/raw_pages-{inv_num}.jsonl.gz"
    preprocessed_pages_file = f"{indexer.base_dir}/pages/preprocessed_page_json/preprocessed_pages-{inv_num}.jsonl.gz"
    if os.path.exists(preprocessed_pages_file):
        if os.path.exists(raw_pages_file):
            # compare timestamps, take latest
            prep_stat = os.stat(preprocessed_pages_file)
            raw_stat = os.stat(raw_pages_file)
            if prep_stat.st_mtime > raw_stat.st_mtime:
                return get_preprocessed_pages(inv_num, indexer)
            else:
                return get_raw_pages(inv_num, indexer)
        else:
            return get_preprocessed_pages(inv_num, indexer)
    elif os.path.exists(raw_pages_file):
        # create preprocessed pages file?
        return get_raw_pages(inv_num, indexer)
    else:
        return None


def get_pages(inv_num: int, indexer: Indexer, page_type: str = None) -> Generator[pdm.PageXMLPage, None, None]:
    if os.path.exists(f"{indexer.base_dir}/pages") is False:
        os.mkdir(f"{indexer.base_dir}/pages")
    page_generator = get_last_pages(inv_num, indexer)
    if page_generator is not None:
        for page in page_generator:
            if page_type is None or page.has_type(page_type):
                yield page
    else:
        logger_string = f"Downloading pages from ES index for inventory {inv_num}"
        logger.info(logger_string)
        print(logger_string)
        pages_file = f"{indexer.base_dir}/pages/raw_page_json/raw_pages-{inv_num}.jsonl.gz"
        pages = [page for page in indexer.rep_es.retrieve_inventory_pages(inv_num)]
        with gzip.open(pages_file, 'wt') as fh:
            for page in pages:
                page_string = json.dumps(page.json)
                fh.write(f"{page_string}\n")
                if page_type is not None and page.has_type(page_type):
                    yield page
    return None


def read_session_start_csv(session_start_file: str):
    with open(session_start_file, 'rt') as fh:
        headers = next(fh).strip('\n').split('\t')
        # print('headers:', headers)
        for line in fh:
            cells = line.strip('\n').split('\t')
            row = {header: cells[hi] for hi, header in enumerate(headers)}
            yield row
    return None


def parse_session_starts_row(start_row: Dict[str, any]):
    num_fields = [
        'scan_num',
        'page_num',
        'year',
        'month_num',
        'day_num',
        'second_session',
        'inv_num'
    ]
    if ',' in start_row['text_region_id']:
        start_row['text_region_id'] = [tr_id.strip() for tr_id in start_row['text_region_id'].split(',')]
        # print('    multi-TR:', start_row['text_region_id'])
    elif 'NL-HaNA_' not in start_row['text_region_id']:
        start_row['text_region_id'] = None
    if ',' in start_row['line_ids']:
        start_row['line_ids'] = [line_id.strip() for line_id in start_row['line_ids'].split(',')]
        # print('    multi-LINE:', start_row['line_ids'])
    elif 'NL-HaNA_' not in start_row['line_ids']:
        start_row['line_ids'] = []
    else:
        start_row['line_ids'] = [start_row['line_ids']]
    for num_field in num_fields:
        if num_field == 'second_session' and num_field not in start_row:
            continue
        if start_row[num_field] == '':
            print(start_row)
            print(f"do_indexing.parse_session_starts_row - num_field {num_field} is empty")
            start_row[num_field] = None
        start_row[num_field] = int(float(start_row[num_field]))
    if start_row['text_region_id'] is None and start_row['line_ids'] == []:
        # print('NO START:', start_row)
        return None
    if start_row['text_region_id'] is not None and start_row['line_ids'] != []:
        # print('both', start_row)
        pass
    start_row['date'] = datetime.date(start_row['year'], start_row['month_num'], start_row['day_num']).isoformat()
    return start_row


def get_session_starts(inv_id: str, starts_only: bool = False, debug: int = 0):
    project_dir = get_project_dir()
    if debug > 1:
        print(f"do_indexing.get_session_starts - project_dir: {project_dir}")
    starts_json_file = os.path.join(project_dir, f"ground_truth/sessions/starts/session_starts-{inv_id}.json")
    starts_csv_file = os.path.join(project_dir, f"ground_truth/sessions/starts/session_starts-{inv_id}.csv")
    if os.path.exists(starts_json_file):
        if debug > 0:
            print(f"do_indexing.get_session_starts - session_starts_file: {starts_json_file}")
        with open(starts_json_file, 'rt') as fh:
            return json.load(fh)
    if os.path.exists(starts_csv_file):
        if debug > 0:
            print(f"do_indexing.get_session_starts - session_starts_file: {starts_csv_file}")
        session_starts = []
        count = 0
        for start_row in read_session_start_csv(starts_csv_file):
            count += 1
            if start_row['page_num'] == '':
                scan_id, coord_string = start_row['line_ids'].split('-line-')
                x = int(coord_string[:4])
                if x < 2000:
                    offset = 2
                elif x > 3000:
                    offset = 1
                else:
                    print(f"do_indexing.get_session_starts - unexpected x-coordnites for line id: {x}")
                    print(f"    start_row: {start_row}")
                    offset = 1
                scan_num = int(scan_id[-4:])
                start_row['page_num'] = scan_num * 2 - offset
                # print(start_row, page_num)
            start_record = parse_session_starts_row(start_row)
            if start_record is None:
                continue
            if starts_only is False:
                session_starts.append(start_record)
            elif start_record is not None and start_record['date_type'] == 'start':
                session_starts.append(start_record)
        return session_starts
    else:
        print('do_indexing.get_session_starts - no starts in JSON or CSV:')
        print(f"   {starts_json_file}")
        print(f"   {starts_csv_file}")
        return None


def check_line_metadata(pages: List[pdm.PageXMLPage]):
    """ensure lines have information on inventory number and id in their metadata."""
    for page in pages:
        if 'series_name' not in page.metadata:
            print(page.metadata)
            raise ValueError(f'No series_name in page.metadata for page {page.id}')
        if 'inventory_id' not in page.metadata:
            page.metadata['inventory_id'] = f"{page.metadata['series_name']}_{page.metadata['inventory_num']}"
        for line in page.get_lines():
            if 'inventory_num' not in line.metadata:
                line.metadata['inventory_num'] = page.metadata['inventory_num']
            if 'inventory_id' not in line.metadata:
                line.metadata['inventory_id'] = page.metadata['inventory_id']
            if 'scan_id' not in line.metadata:
                print(line.metadata)
                raise ValueError(f"no scan_id in line.metadata for line {line.id}")


def update_page_metadata(page: pdm.PageXMLPage,
                         text_page_num_map: Dict[int, Dict[str, Union[int, str]]],
                         page_type_index: Dict[int, Union[str, List[str]]],
                         nlc_gysbert: NeuralLineClassifier = None, debug: int = 0):
    if page.metadata['page_num'] in text_page_num_map:
        page_num = page.metadata['page_num']
        page.metadata['text_page_num'] = text_page_num_map[page_num]['text_page_num']
        page.metadata['skip'] = text_page_num_map[page_num]['skip']
        if debug > 0:
            print(f"do_indexing.update_page_metadata - adding text_page_num_map skip {page.metadata['skip']}")
        if text_page_num_map[page_num]['problem'] is not None:
            page.metadata['problem'] = text_page_num_map[page_num]['problem']
    if page_type_index is None:
        page.add_type('unknown')
        page.metadata['type'] = [ptype for ptype in page.type]
    elif page.metadata['page_num'] not in page_type_index:
        page.add_type("empty_page")
        page.metadata['type'] = [ptype for ptype in page.type]
        page.metadata['skip'] = True
        if debug > 0:
            print(f"do_indexing.update_page_metadata - adding missing page_type_index skip {page.metadata['skip']}")
        # print("page without page_num:", page.id)
        # print("\tpage stats:", page.stats)
    else:
        page_types = page_type_index[page.metadata['page_num']]
        if isinstance(page_types, str):
            page_types = [page_types]
        for page_type in page_types:
            page.add_type(page_type)
        page.metadata['type'] = [ptype for ptype in page.type]
        page.metadata['skip'] = False
        if debug > 0:
            print(f"do_indexing.update_page_metadata - adding existing page_type_index skip {page.metadata['skip']}")
    predicted_line_class = nlc_gysbert.classify_page_lines(page) if nlc_gysbert else {}
    for tr in page.get_all_text_regions():
        for line in tr.lines:
            if line.text is not None and line.text.startswith('Alsoo'):
                line.metadata['line_class'] = 'para_start'
            line.metadata['text_region_id'] = tr.id
            if line.id in predicted_line_class:
                line.metadata['line_class'] = predicted_line_class[line.id]
            elif 'line_class' in line.metadata:
                continue
            else:
                line.metadata['line_class'] = 'unknown'


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
        elif indexing_step == 'full_resolutions':
            if indexing_label is None:
                self.rep_es.config['resolutions_index'] = 'full_resolutions'
            elif indexing_label == 'staging':
                self.rep_es.config['resolutions_index'] = f'full_resolutions_{indexing_label}'
                # self.rep_es.config['session_metadata_index'] = f'session_metadata_{indexing_label}'
                # self.rep_es.config['session_text_region_index'] = f'session_text_regions_{indexing_label}'
            else:
                self.rep_es.config['resolutions_index'] = f'full_resolutions_{indexing_label}'
            if debug > 0:
                print(f"Indexer.set_indexes - setting:")
                print(f"\tresolutions_index index to {self.rep_es.config['resolutions_index']}")
                print(f"\tsession_metadata_index index to {self.rep_es.config['session_metadata_index']}")
                print(f"\tsession_text_region_index index to {self.rep_es.config['session_text_region_index']}")
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

    def do_page_extracting_from_scan(self, inv_num: int):
        inv_metadata = get_inventory_by_num(inv_num)
        page_type_index = get_per_page_type_index(inv_metadata)
        text_page_num_map = map_text_page_nums(inv_metadata)
        page_count = 0
        nlc_gysbert = None
        if inv_num < 3760 or inv_num > 3864:
            model_dir = 'data/models/neural_line_classification/nlc_gysbert_model'
            nlc_gysbert = NeuralLineClassifier(model_dir)
        for si, scan in enumerate(self.rep_es.retrieve_inventory_scans(inv_num)):
            if 'scan_width' not in scan.metadata:
                scan.metadata['scan_width'] = scan.coords.width
                scan.metadata['scan_height'] = scan.coords.height
            if 'scan_num' not in scan.metadata:
                scan.metadata['scan_num'] = int(scan.id.split('_')[-1])
            try:
                pages = pagexml_parser.split_pagexml_scan(scan, page_type_index, debug=0)
            except Exception as err:
                logger.error(err)
                logger.info('Error splitting pages of scan', scan.id)
                print('Error splitting pages of scan', scan.id)
                raise
            for page in pages:
                page_count += 1
                update_page_metadata(page, text_page_num_map, page_type_index, nlc_gysbert)
                yield page
            if (si+1) % 100 == 0:
                logger.info(f"{si+1} scans processed")
                print(f"{si+1} scans processed")

    def do_page_writing(self, inv_num: int, year_start: int, year_end: int):
        self.do_raw_page_writing(inv_num, year_start, year_end)
        self.do_preprocessed_page_writing(inv_num, year_start, year_end)

    def do_raw_page_writing(self, inv_num: int, year_start: int, year_end: int):
        inv_metadata = get_inventory_by_num(inv_num)
        num_scans = inv_metadata['num_scans']
        message = f"Writing raw pagexml pages for inventory {inv_num} (years {year_start}-{year_end})..."
        logger.info(message)
        print(message)
        raw_page_dir = 'data/pages/raw_page_json'
        if os.path.exists(raw_page_dir) is False:
            os.mkdir(raw_page_dir)
        raw_page_file = f"{raw_page_dir}/raw_pages-{inv_num}.jsonl.gz"
        raw_pages = []
        for pi, page in enumerate(self.do_page_extracting_from_scan(inv_num)):
            page_count = pi + 1
            raw_pages.append(page)
            message = (f"extracting page {page_count} (scan {page.metadata['scan_num']} "
                       f"of {num_scans}) with id {page.id}")
            logger.info(message)
            print(message)
        write_pages(raw_page_file, raw_pages)

    def do_preprocessed_page_writing(self, inv_num: int, year_start: int, year_end: int):
        inv_metadata = get_inventory_by_num(inv_num)
        if get_text_type(inv_num) in {'printed', 'gedrukt'} or inv_metadata['content_type'] != 'resolutions':
            return None
        preprocessed_page_dir = 'data/pages/preprocessed_page_json'
        if os.path.exists(preprocessed_page_dir) is False:
            os.mkdir(preprocessed_page_dir)
        message = f"Writing preprocessed pagexml pages for inventory {inv_num} (years {year_start}-{year_end})..."
        logger.info(message)
        print(message)

        raw_pages = [page for page in get_raw_pages(inv_num, self)]
        print(f"number of raw pages: {len(raw_pages)}")
        check_element_types(raw_pages)

        res_pages = filter_pages(raw_pages, 'resolution_page')
        other_pages = [page for page in raw_pages if page not in res_pages]
        print(f"number of res_pages: {len(res_pages)}\tnumber of other pages: {len(other_pages)}")

        date_region_classifier = load_date_region_classifier()
        date_trs = get_header_dates(res_pages)
        print(f"inv {inv_num}  number of date text_regions in raw pages: {len(date_trs)}")

        date_tr_type_map = classify_page_date_regions(res_pages, date_region_classifier)
        preprocessed_page_file = f"{preprocessed_page_dir}/preprocessed_pages-{inv_num}.jsonl.gz"
        preprocessed_pages = process_handwritten_pages(inv_metadata['inventory_id'], res_pages,
                                                       date_tr_type_map=date_tr_type_map, ignorecase=False,
                                                       debug=0)

        check_element_types(preprocessed_pages)
        date_trs = get_header_dates(preprocessed_pages)
        print(f"inv {inv_num}  number of date text_regions in preprocessed pages: {len(date_trs)}")

        preprocessed_pages.extend(other_pages)
        preprocessed_pages = sorted(preprocessed_pages, key=lambda p: p.id)
        write_pages(preprocessed_page_file, preprocessed_pages)

    def do_page_indexing_pagexml(self, inv_num: int, year_start: int, year_end: int,
                                 page_generator: Generator[pdm.PageXMLPage, None, None]):
        logger.info(f"Indexing pagexml pages for inventory {inv_num} (years {year_start}-{year_end})...")
        print(f"Indexing pagexml pages for inventory {inv_num} (years {year_start}-{year_end})...")
        inv_metadata = get_inventory_by_num(inv_num)
        num_scans = inv_metadata['num_scans']
        for pi, page in enumerate(page_generator):
            page_count = pi + 1
            message = f"indexing page {page_count} (scan {page.metadata['scan_num']} of {num_scans}) with id {page.id}"
            logger.info(message)
            print(message)
            prov_url = self.rep_es.post_provenance([page.metadata['scan_id']], [page.id], 'scans', 'pages')
            page.metadata['provenance_url'] = prov_url
            self.rep_es.index_page(page)

    def do_page_indexing_pagexml_from_file(self, inv_num: int, year_start: int, year_end: int):
        page_generator = get_pages(inv_num, self)
        self.do_page_indexing_pagexml(inv_num, year_start, year_end, page_generator)

    def do_page_indexing_pagexml_from_scans(self, inv_num: int, year_start: int, year_end: int):
        page_generator = self.do_page_extracting_from_scan(inv_num)
        self.do_page_indexing_pagexml(inv_num, year_start, year_end, page_generator)

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
                # return None
        else:
            session_starts = None

        pages = [page for page in get_pages(inv_num, self, page_type='resolution_page')]
        pages.sort(key=lambda page: page.metadata['page_num'])
        check_line_metadata(pages)
        print(f'inventory {inv_num} - number of pages: {len(pages)}')
        page_type_index = get_per_page_type_index(inv_metadata)
        text_page_num_map = map_text_page_nums(inv_metadata)
        for page in pages:
            update_page_metadata(page, text_page_num_map, page_type_index)
        pages = [page for page in pages if "skip" not in page.metadata or page.metadata["skip"] is False]
        print(f'inventory {inv_num} - number of non-skipped pages: {len(pages)}')

        # include_variants not yet implemented in FuzzyTokenSearcher so use FuzzyPhraseSearcher
        # use_token_searcher = True if text_type in {'printed', 'gedrukt'} else False
        use_token_searcher = False
        if text_type in {'printed', 'gedrukt'}:
            session_gen = get_printed_sessions(inventory_id=inv_id, pages=pages,
                                               session_starts=session_starts,
                                               use_token_searcher=use_token_searcher, debug=0)
        else:
            num_future_dates = 31
            num_past_dates = 5
            if inv_metadata['year_start'] < 1630:
                num_future_dates = 61
                num_past_dates = 10
            if inv_metadata['year_end'] - inv_metadata['year_start'] > 3:
                num_future_dates = 101
                num_past_dates = 15
            elif 1 < inv_metadata['year_end'] - inv_metadata['year_start'] <= 3:
                num_future_dates = 61
                num_past_dates = 10
            session_gen = get_handwritten_sessions(inv_id, pages=pages, session_starts=session_starts,
                                                   do_preprocessing=False,
                                                   num_past_dates=num_past_dates,
                                                   num_future_dates=num_future_dates, debug=0)
        print(f"text_type: {text_type}")
        prev_session = None
        try:
            for session in session_gen:
                yield session
                prev_session = session
        except Exception as err:
            if prev_session is not None:
                logger_string = f'last successful session: {prev_session.id}'
            else:
                logger_string = f'last successful session: {prev_session}'
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

    def remove_inventory_docs_from_index(self, index: str, inv_metadata: Dict[str, any]):
        message = f"deleting inventory {inv_metadata['inventory_id']} from index {index}"
        logger.info(message)
        print(message)
        response = self.rep_es.delete_by_inventory(index, inv_num=inv_metadata['inventory_num'])
        logger.info(f'ES response: {response}')
        print(f'ES response: {response}\n')

    def do_session_indexing(self, inv_num: int, year_start: int, year_end: int, from_files: bool = False,
                            from_starts: bool = False):
        logger.info(f"Indexing PageXML sessions for inventory {inv_num} (years {year_start}-{year_end})...")
        print(f"Indexing PageXML sessions for inventory {inv_num} (years {year_start}-{year_end})...")
        inv_metadata = get_inventory_by_num(inv_num)
        self.remove_inventory_docs_from_index(self.rep_es.config['session_metadata_index'],
                                              inv_metadata=inv_metadata)
        self.remove_inventory_docs_from_index(self.rep_es.config['session_text_region_index'],
                                              inv_metadata=inv_metadata)
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
                session_json['evidence'] = [match.json() for match in session.evidence]
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
                print(f"WARNING do_indexing.get_inventory_sessions - tr.metadata has no 'session_id' key")
                continue
            if isinstance(tr.metadata['session_id'], list):
                for session_id in tr.metadata['session_id']:
                    inv_session_trs[session_id].append(tr)
            else:
                inv_session_trs[tr.metadata['session_id']].append(tr)
        for session_meta in inv_session_metas:
            try:
                session_id = session_meta['id']
                if session_id not in inv_session_trs:
                    print(f're-indexing text regions for session {session_id}')
                    session_trs = self.rep_es.retrieve_session_trs_by_metadata(session_meta)
                    for tr in session_trs:
                        tr.metadata['inventory_num'] = session_meta['metadata']['inventory_num']
                        if tr.metadata['session_id'] != session_id:
                            if isinstance(tr.metadata['session_id'], str):
                                tr.metadata['session_id'] = [tr.metadata['session_id']]
                            tr.metadata['session_id'].append(session_id)
                        for line in tr.lines:
                            line.metadata['inventory_num'] = session_meta['metadata']['inventory_num']
                    session_trs_json = [tr.json for tr in session_trs]
                    self.rep_es.index_bulk_docs(self.rep_es.config['session_text_region_index'],
                                                session_trs_json)
                    inv_session_trs[session_id] = session_trs
                session = make_session_from_meta_and_trs(session_meta, inv_session_trs[session_meta['id']])
                # session = rdm.Session(doc_id=session_meta['id'], session_data=session_meta,
                #                       text_regions=inv_session_trs[session_meta['id']])
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
        print(f"\n\n-------------\n{self.rep_es.config['resolutions_index']}\n\n-------------\n")
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
                resolutions = [res for res in hand_res_parser.get_session_resolutions(session,
                                                                                      opening_searcher, debug=0)]
                session_tr_urls = make_index_urls(es_config=self.rep_es.es_anno_config,
                                                  doc_ids=[tr.id for tr in session.text_regions],
                                                  index='session_text_regions')
                source_ids = [session.id]
                target_ids = [res.id for res in resolutions]
                why = f'REPUBLIC CAF Pipeline deriving resolutions from session_metadata and session_text_regions'
                prov_url = self.rep_es.post_provenance(source_ids=source_ids,
                                                       target_ids=target_ids,
                                                       source_index='session_metadata',
                                                       target_index='resolutions',
                                                       source_external_urls=session_tr_urls,
                                                       ignore_prov_errors=True,
                                                       why=why)
                for resolution in resolutions:
                    resolution.metadata['prov_url'] = prov_url
                    print('indexing handwritten resolution', resolution.id)
                    # self.rep_es.index_resolution(resolution)
                resolutions_json = [res.json for res in resolutions]
                # print('using resolution index', self.rep_es.config['resolutions_index'])
                self.rep_es.index_bulk_docs(self.rep_es.config['resolutions_index'], resolutions_json)
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
        inv_metadata = get_inventory_by_num(inv_num)
        # make sure previous resolutions from inventory are removed
        self.rep_es.delete_by_inventory(inv_num=inv_num, index=self.rep_es.config['resolutions_index'])
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
                message = f'\tadding resolution metadata for resolution {new_resolution.id}'
                logger.info(message)
                print(message)
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
    inv_metadata = get_inventory_by_num(task['inv_num'])
    text_type = get_text_type(task['inv_num'])
    if inv_metadata is None:
        message = f"Skipping {task['indexing_step']} for inventory {task['inv_num']} " \
                  f"(years {task['year_start']}-{task['year_end']})..."
        logger.info(message)
        print(message)
        return None
    print("TASK:", task)
    if inv_metadata['content_type'] == 'index':
        # inventories that only contain indexes can be skip for
        # parsing sessions, resolutions and attendance lists
        if any([level in task['indexing_step'] for level in ['resolution', 'session', 'attendance']]):
            return None
    indexer.set_indexes(task["indexing_step"], task["index_label"], debug=1)
    # print('process_inventory - index:', indexer.rep_es.config['resolutions_index'])
    if task["indexing_step"] == "download":
        indexer.do_downloading(task["inv_num"], task["year_start"], task["year_end"])
    elif task["indexing_step"] == "download_pages":
        indexer.download_pages(task["inv_num"], task["year_start"], task["year_end"])
    elif task["indexing_step"] == "scans_pages":
        indexer.do_scan_indexing_pagexml(task["inv_num"], task["year_start"], task["year_end"])
        indexer.do_page_indexing_pagexml_from_scans(task["inv_num"], task["year_start"], task["year_end"])
    elif task["indexing_step"] == "scans":
        indexer.do_scan_indexing_pagexml(task["inv_num"], task["year_start"], task["year_end"])
    elif task["indexing_step"] == "write_raw_pages":
        indexer.do_raw_page_writing(task["inv_num"], task["year_start"], task["year_end"])
    elif task["indexing_step"] == "write_preprocessed_pages":
        indexer.do_preprocessed_page_writing(task["inv_num"], task["year_start"], task["year_end"])
    elif task["indexing_step"] == "write_pages":
        indexer.do_raw_page_writing(task["inv_num"], task["year_start"], task["year_end"])
        indexer.do_preprocessed_page_writing(task["inv_num"], task["year_start"], task["year_end"])
    elif task["indexing_step"] == "pages":
        indexer.do_page_writing(task["inv_num"], task["year_start"], task["year_end"])
        indexer.do_page_indexing_pagexml_from_file(task["inv_num"], task["year_start"], task["year_end"])
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
        if text_type == 'printed' or text_type == 'gedrukt':
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
                if re.match(r"\d+,\d+", arg):
                    start = [int(ele) for ele in arg.split(',')]
                else:
                    start = int(arg)
            if opt == '-e':
                end = int(arg)
            if opt == '-i':
                indexing_step = arg
            if opt == '-l':
                index_label = arg
            if opt == '-b':
                base_dir = arg
        if start is not None and end is None:
            end = start
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

    print(f'do_indexing.get_tasks - index_label: {index_label}')
    print(f'start: {start}\tend: {end}')
    inv_nums = []
    if isinstance(start, list):
        inv_nums = start
    else:
        inv_nums = [inv for inv in range(start, end+1)]
    tasks = []
    for inv_num in inv_nums:
        inv_map = get_inventory_by_num(inv_num)
        if 'session' in indexing_step and inv_map['content_type'] != 'resolutions':
            continue
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
        if 'session' in indexing_step or 'resolution' in indexing_step and index_label is None:
            index_label = "staging"
        tasks = get_tasks(start, end, indexing_step, index_label, host_type, base_dir)
        print('index_label:', index_label)
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
