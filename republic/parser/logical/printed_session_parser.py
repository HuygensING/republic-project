import copy
import datetime
import json
import re
from typing import List, Dict, Generator, Iterator, Tuple, Union
from collections import defaultdict

import pagexml.model.physical_document_model as pdm
from fuzzy_search.match.phrase_match import PhraseMatch
# from pagexml.model.physical_document_model import PageXMLPage, PageXMLTextLine, PageXMLTextRegion
# from pagexml.model.physical_document_model import parse_derived_coords

import republic.model.republic_document_model as  rdm
from republic.analyser.quality_control import check_session
from republic.model.inventory_mapping import get_inventory_by_id
from republic.model.republic_phrase_model import session_phrase_model
from republic.model.republic_date import RepublicDate, derive_date_from_string
from republic.model.republic_date import DateNameMapper
from republic.model.republic_date import get_next_workday
from republic.model.republic_date import get_next_date_strings
from republic.model.republic_date import make_republic_date
from republic.model.republic_date import exception_dates
from republic.model.republic_date_phrase_model import date_name_map as default_date_name_map
from republic.model.republic_session import SessionSearcher, calculate_work_day_shift
from republic.model.republic_session import session_opening_element_order
from republic.model.republic_document_model import Session
from republic.helper.pagexml_helper import sort_lines_in_reading_order
from republic.helper.metadata_helper import doc_id_to_iiif_url
from republic.parser.logical.date_parser import get_date_token_cat
from republic.parser.logical.date_parser import get_session_date_line_structure
from republic.parser.logical.date_parser import get_session_date_lines_from_pages
from republic.parser.logical.generic_logical_parser import copy_line


def initialize_inventory_date(inv_metadata: dict, date_mapper: DateNameMapper, debug: int = 0) -> RepublicDate:
    year, month, day = [int(part) for part in inv_metadata['period_start'].split('-')]
    if month == 1 and day == 1:
        day = 2
    if debug > 0:
        print(f'initialize_inventory_date - year, month, day: {year} {month} {day}')
    return RepublicDate(year, month, day, date_mapper=date_mapper)


def stream_handwritten_page_lines(page: pdm.PageXMLPage,
                                  include_marginalia: bool = False) -> Generator[pdm.PageXMLTextLine, None, None]:
    if include_marginalia:
        trs = [tr for column in page.columns for tr in column.text_regions]
    else:
        trs = [tr for column in page.columns for tr in column.text_regions if not page.has_type('marginalia')]
    for tr in page.extra:
        # make sure the session date is part of the column because the
        # session parser needs it
        if tr.has_type('date'):
            for column in page.columns:
                if pdm.is_horizontally_overlapping(tr, column) and tr not in column.text_regions:
                    # print("adding extra tr to column")
                    column.text_regions.append(tr)
                    trs.append(tr)
                    for line in tr.lines:
                        line.metadata["column_id"] = column.id
            # if not add_column:
            #     print("TR:", tr.id)
            #     for col in page.columns:
            #         print("\tCOL:", col.id)
    for tr in sorted(trs):
        for line in tr.lines:
            line.metadata['text_region_id'] = tr.id
            line.metadata['inventory_id'] = page.metadata['inventory_id']
            yield line


def stream_resolution_page_lines(inventory_id: str, pages: List[pdm.PageXMLPage]) -> Generator[pdm.PageXMLTextLine, None, None]:
    """Iterate over list of pages and return a generator that yields individuals lines.
    Iterator iterates over columns and textregions.
    Assumption: lines are returned in reading order."""
    sorted_pages = sort_inventory_pages(inventory_id, pages)
    for page in sorted_pages:
        if "text_type" in page.metadata and page.metadata["text_type"] == "handwritten":
            for line in stream_handwritten_page_lines(page):
                line.metadata['inventory_id'] = page.metadata['inventory_id']
                yield line
        elif not page.columns:
            continue
        else:
            for line in sort_lines_in_reading_order(page):
                line.metadata['inventory_id'] = page.metadata['inventory_id']
                yield line


def score_session_opening_elements(session_opening_elements: Dict[str, int], num_elements_threshold: int) -> float:
    """Order session elements by text order and check against expected order. If enough elements are
    in expected order, the number of ordered elements is returned as the score, otherwise score is zero."""
    opening_elements = sorted(session_opening_elements.items(), key=lambda x: x[1])
    if len(session_opening_elements.keys()) < num_elements_threshold:
        # we need at least num_elements_threshold elements to determine this is a new session date
        return 0
    try:
        numbered_opening_elements = [session_opening_element_order.index(element[0]) for element in opening_elements]
    except ValueError:
        print(session_opening_elements)
        raise
    if len(set(opening_elements)) <= 3:
        return 0
    order_score = score_opening_element_order(numbered_opening_elements)
    return order_score


def score_opening_element_order(opening_element_list: List[any]) -> float:
    """Score the found session opening elements on how well they match the expected order."""
    opening_element_set = sorted(list(set(opening_element_list)))
    count = 0
    dummy_list = copy.copy(opening_element_list)
    for i, e1 in enumerate(dummy_list):
        first = opening_element_list.index(e1)
        rest = opening_element_list[first+1:]
        for e2 in rest:
            if e2 > e1:
                count += 1
    set_size = len(opening_element_set)
    order_max = set_size * (set_size - 1) / 2
    order_score = count / order_max
    return order_score


def find_session_line(line_id: str, session_lines: List[pdm.PageXMLTextLine]) -> pdm.PageXMLTextLine:
    """Find a specific line by id in the list of lines belonging to a session."""
    for line in session_lines:
        if line.id == line_id:
            return line
    raise IndexError(f'Line with id {line_id} not in session lines.')


def generate_session_doc(inv_metadata: Dict[str, any], session_metadata: Dict[str, any],
                         session_date_metadata: Dict[str, any],
                         session_lines: List[pdm.PageXMLTextLine],
                         session_searcher: SessionSearcher, column_metadata: Dict[str, dict],
                         page_index: Dict[str, pdm.PageXMLPage], debug: int = 0) -> iter:
    evidence = session_metadata['evidence']
    if evidence is None or len(evidence) == 0:
        print(f"WARNING - session {session_metadata['session_id']} has no evidence")
    # print('\ngenerate_session_doc - evidence:', [match.phrase.phrase_string for match in evidence])
    # print('\n')
    date_line_id = session_date_metadata['line_id']
    del session_metadata['evidence']
    text_region_lines = defaultdict(list)
    text_regions: List[pdm.PageXMLTextRegion] = []
    scan_version = {}
    session_text_page_nums = set()
    session_page_ids = set()
    for line in session_lines:
        if 'inventory_num' not in line.metadata:
            line.metadata['inventory_num'] = inv_metadata['inventory_num']
        if 'inventory_id' not in line.metadata:
            line.metadata['inventory_id'] = inv_metadata['inventory_id']
        if "column_id" not in line.metadata:
            print(line.id, line.parent.id, line.parent.type)
            print(line.parent.parent.id)
        text_region_id = line.metadata['column_id']
        text_region_lines[text_region_id].append(copy_line(line))
        # text_region_lines[text_region_id].append(line)
    for text_region_id in text_region_lines:
        if text_region_id not in column_metadata:
            print(f'printed_session_parser.generate_session_doc - text_region_id {text_region_id}'
                  f'not in column_metadata')
            for line in text_region_lines[text_region_id]:
                if line.metadata['column_id'] == text_region_id:
                    print('\tline.metadata:', line.metadata)
                    print('\tline.text:', line.text)
        metadata = column_metadata[text_region_id]
        source_page_id = metadata['page_id']
        source_page = page_index[source_page_id]
        parent = text_region_lines[text_region_id][0].parent
        # print('FIRST PARENT:')
        # print(json.dumps(parent.metadata, indent=4))
        coords = pdm.parse_derived_coords(text_region_lines[text_region_id])
        text_region = pdm.PageXMLTextRegion(doc_id=text_region_id, metadata=metadata,
                                            coords=coords, lines=text_region_lines[text_region_id])
        text_region.set_derived_id(text_region.metadata['scan_id'])
        if any([line.id == date_line_id for line in text_region.lines]):
            if debug > 0:
                print('printed_session_parser.generate_session_doc - '
                      'text_region has session date line:', text_region.id)
            session_date_metadata['text_region_id'] = text_region.id
        text_region.metadata["iiif_url"] = doc_id_to_iiif_url(text_region.id)
        if 'inventory_num' not in text_region.metadata:
            text_region.metadata['inventory_num'] = inv_metadata['inventory_num']
        if 'inventory_id' not in text_region.metadata:
            text_region.metadata['inventory_id'] = inv_metadata['inventory_id']
        if 'session_id' not in text_region.metadata:
            text_region.metadata['session_id'] = session_metadata['session_id']
        if text_region.metadata['session_id'] != session_metadata['session_id']:
            text_region.metadata['session_id'] = session_metadata['session_id']
        # We're going from physical to logical structure here, so add a trace to the
        # logical structure elements about where they come from in the physical
        # structure, especially the printed page number needed for linking to locators
        # in the index pages.
        # print('START TEXTREGION:')
        # print(json.dumps(text_region.metadata, indent=4))
        # print('FIRST LINE:')
        first_line = text_region_lines[text_region_id][0]
        # print(json.dumps(first_line.metadata, indent=4))
        # while "resolution_page" not in parent.type and parent.parent:
        #     parent = parent.parent
            # print('NEXT PARENT:')
            # print(json.dumps(parent.metadata, indent=4))
        if source_page:
            if "textrepo_version" in source_page.metadata:
                scan_version[source_page.metadata['scan_id']] = source_page.metadata['textrepo_version']
            text_region.metadata['page_id'] = source_page.id
            if 'page_num' not in source_page.metadata:
                print('MISSING PAGE_NUM')
                print(json.dumps(source_page.metadata, indent=4))
            text_region.metadata['page_num'] = source_page.metadata['page_num']
            if "text_page_num" not in source_page.metadata:
                pass
                # print("MISSING text_page_num for page", source_page.id)
            else:
                text_region.metadata['text_page_num'] = source_page.metadata['text_page_num']
                if isinstance(source_page.metadata["text_page_num"], int):
                    session_text_page_nums.add(source_page.metadata['text_page_num'])
                    session_page_ids.add(source_page.id)
        text_regions.append(text_region)
    for scan_id in scan_version:
        scan_version[scan_id]['scan_id'] = scan_id
    # print('\ngenerate_session_doc - metadata:', session_metadata)
    # print('\n')
    session = Session(doc_id=session_metadata['session_id'], metadata=session_metadata,
                      date_metadata=session_date_metadata,
                      text_regions=text_regions, evidence=evidence, scan_versions=list(scan_version.values()),
                      date_mapper=session_searcher.date_mapper)
    session_metadata["text_page_num"] = sorted(list(session_text_page_nums))
    session.metadata["text_page_num"] = sorted(list(session_text_page_nums))
    session.metadata["page_ids"] = sorted(list(session_page_ids))
    # session.add_page_text_region_metadata(column_metadata)
    # add number of lines to session info in session searcher
    session_info = session_searcher.sessions[session_metadata['session_date']][-1]
    session_info['num_lines'] = len(session_lines)
    # print('this sessions contains elements from the following scans:', session.scan_versions)
    # print('\ngenerate_session_doc - session.date:', session.date)
    # print('\n')
    if session.date_metadata['text_region_id'] is not None and \
            any([tr.id == session.date_metadata['text_region_id'] for tr in session.text_regions]) is False:
        raise ValueError(f"the text_region_id in the session.date_metadata "
                         f"({session.date_metadata['text_region_id']}) "
                         f"does not correspond with any of the text region ids")
    if session.date.is_rest_day() or not session_searcher.has_session_date_match():
        return session
    # Check if the next session date is more than 1 workday ahead
    date_match = session_searcher.get_session_date_match()
    new_date = derive_date_from_string(date_match.phrase.phrase_string, session_searcher.year,
                                       date_mapper=session_searcher.date_mapper)
    if session.date.isoformat() == new_date.isoformat():
        # print('SAME DAY:', session_searcher.current_date.isoformat(), '\t', session.date.isoformat())
        return session
    workday_shift = calculate_work_day_shift(new_date, session.date, date_mapper=session_searcher.date_mapper)
    # print('workday_shift:', workday_shift)
    if workday_shift > 1:
        if debug > 0:
            print('MEETING DOC IS MULTI DAY')
        session.metadata['date_shift_status'] = 'multi_day'
    return session


def clean_lines(lines: List, clean_copy=True) -> List:
    if clean_copy:
        lines = copy.deepcopy(lines)
    for line in lines:
        del line['metadata']['scan_num']
        del line['metadata']['doc_id']
        del line['metadata']['column_id']
        del line['metadata']['textregion_id']
        del line['metadata']['line_index']
        del line['metadata']['scan_version']
    return lines


class GatedWindow:

    def __init__(self, window_size: int = 10, open_threshold: int = 300, shut_threshold: int = 400):
        self.window_size = window_size
        self.middle_doc = int(window_size/2)
        # fill the sliding window with empty elements, so that first documents are appended at the end.
        self.sliding_window: List[Union[None, pdm.PageXMLTextLine]] = [None] * window_size
        self.open_threshold = open_threshold
        self.shut_threshold = shut_threshold
        self.gate_open = False
        self.num_chars = 0
        self.let_through: List[bool] = [False] * window_size

    def add_line(self, line: pdm.PageXMLTextLine):
        """Add a document to the sliding window. doc should be a dictionary with
        the 'text' property containing the document text."""
        if len(self.sliding_window) >= self.window_size:
            self.sliding_window = self.sliding_window[-self.window_size+1:]
            self.let_through = self.let_through[-self.window_size+1:]
        self.let_through += [False]
        self.sliding_window += [line]
        self.check_treshold()

    def num_chars_in_window(self) -> int:
        """Return the number of characters in the sliding window documents."""
        return sum([len(line.text) for line in self.sliding_window if line])

    def check_treshold(self) -> None:
        """Check whether the number of characters in the sliding window crosses
        the current threshold and set let_through accordingly."""
        if self.sliding_window[self.middle_doc] is None:
            # If the sliding window is not filled yet, the middle doc is not let through
            pass
        elif self.num_chars_in_window() < self.shut_threshold:
            self.let_through[self.middle_doc] = True

    def get_first_doc(self) -> Union[None, pdm.PageXMLTextLine]:
        """Return the first sentence in the sliding window if it is set to be let through, otherwise return None."""
        return self.sliding_window[0] if self.let_through[0] else None


def get_columns_metadata(sorted_pages: List[pdm.PageXMLPage]) -> Dict[str, dict]:
    column_metadata = {}
    for page in sorted_pages:
        for column in page.columns:
            if 'scan_id' not in column.metadata:
                raise KeyError('column is missing scan_id')
            if 'page_id' not in column.metadata:
                print('page:', page.id)
                print('column:', column.id)
                print('column metadata:', column.metadata)
                raise KeyError('column is missing page_id')
            column_id = column.id
            column_metadata[column_id] = copy.deepcopy(column.metadata)
            if "textrepo_version" in page.metadata:
                column_metadata['textrepo_version'] = page.metadata['textrepo_version']
            else:
                column_metadata['textrepo_version'] = None
    return column_metadata


def get_printed_date_elements(inv_metadata: Dict[str, any]) -> List[Tuple[str, str]]:
    date_elements = []
    for name_map in default_date_name_map:
        if name_map['period_start'] <= inv_metadata['year_start'] and \
                inv_metadata['year_end'] <= name_map['period_end']:
            date_elements.append(('week_day_name', name_map['week_day_name']))
            date_elements.append(('den', True))
            date_elements.append(('month_day_name', name_map['month_day_name']))
            date_elements.append(('month_name', name_map['month_name']))
            # date_elements.append(('year', False))
    return date_elements


def get_date_mapper(inv_metadata: Dict[str, any], pages: List[pdm.PageXMLPage],
                    ignorecase: bool = True, debug: int = 0):
    inv_id = inv_metadata['inventory_id']
    pages.sort(key=lambda page: page.id)
    # date_token_cat = get_date_token_cat(inv_num=inv_metadata['inventory_num'], ignorecase=ignorecase)
    # session_date_lines = get_session_date_lines_from_pages(pages, filter_date_starts=False)
    if 3760 <= inv_metadata['inventory_num'] <= 3805:
        date_type = 'printed_early'
    elif 3806 <= inv_metadata['inventory_num'] <= 3864:
        date_type = 'printed_late'
    else:
        raise ValueError(f"inventory_num {inv_metadata['inventory_num']} is not a printed volume")
    date_line_structure = [
        ('week_day_name', date_type),
        ('den', 'all'),
        ('month_day_name', 'decimal'),
        ('month_name', date_type)
    ]
    """
    if debug > 2:
        # print(f"printed_session_parser.get_date_mapper - date_token_cat:", date_token_cat)
        print(f"printed_session_parser.get_date_mapper - session_date_lines:", session_date_lines)
    if len(session_date_lines) < 5:
        date_line_structure = get_printed_date_elements(inv_metadata)
    else:
        date_line_structure = get_session_date_line_structure(session_date_lines, date_token_cat, inv_id)
    if 'week_day_name' not in [element[0] for element in date_line_structure]:
        print('WARNING: printed_session_parser.get_date_mapper - '
              'missing week_day_name in date_line_structure for inventory', inv_metadata['inventory_num'])
        print(f"\tdate_line_structure:", date_line_structure)
        return None
    """

    if debug > 2:
        print(f"printed_session_parser.get_date_mapper - date_line_structure:", date_line_structure)
    return DateNameMapper(inv_metadata, date_line_structure)


def sort_inventory_pages(inv_id: str, pages: List[pdm.PageXMLPage], debug: int = 0) -> List[pdm.PageXMLPage]:
    sorted_pages = sorted(pages, key=lambda page: page.metadata['page_num'])
    for page in sorted_pages:
        if 'inventory-id' not in page.metadata:
            if debug > 2:
                print(f'printed_session_parser.sort_inventory_pages - page {page.id} metadata missing inventory {inv_id}')
            page.metadata['inventory_id'] = inv_id
    sort_swaps = {
        'NL-HaNA_1.01.02_3845': [
            {
                'page_ids': [
                    "NL-HaNA_1.01.02_3845_0287-page-572",
                    "NL-HaNA_1.01.02_3845_0287-page-573",
                    "NL-HaNA_1.01.02_3845_0288-page-574",
                    "NL-HaNA_1.01.02_3845_0288-page-575",
                    "NL-HaNA_1.01.02_3845_0289-page-576",
                    "NL-HaNA_1.01.02_3845_0289-page-577",
                ],
                'index_order': [0, 3, 4, 1, 2, 5]
            }
        ]
    }
    page_ids = [page.id for page in sorted_pages]
    if inv_id in sort_swaps:
        print(f"printed_session_parser.sort_inventory_pages - sort_swaps for inventory {inv_id}")
        for swap_set in sort_swaps[inv_id]:
            first, last = swap_set['page_ids'][0], swap_set['page_ids'][-1]
            fi, li = page_ids.index(first), page_ids.index(last)
            if debug > 2:
                print('\tnum_pages:', len(sorted_pages))
                print('\tfi, li:', fi, li)
            pre_pages = pages[:fi]
            post_pages = pages[li+1:]
            swap_pages = pages[fi:li+1]
            if debug > 2:
                print('\tlen(pre_pages):', len(pre_pages))
                print('\tlen(post_pages):', len(post_pages))
                print('\tlen(swap_pages):', len(swap_pages))
            swapped_pages = [swap_pages[i] for i in swap_set['index_order']]
            sorted_pages = pre_pages + swapped_pages + post_pages
            if debug > 1:
                print('swapped page_ids:', [page.id for page in swapped_pages])
    return sorted_pages


def make_start_iterator(session_starts: List[Dict[str, any]]):
    idx = 0

    def start_iterator():
        nonlocal idx
        if idx >= len(session_starts):
            return None
        session_start = session_starts[idx]
        idx += 1
        return session_start

    return start_iterator


def select_date_line_matches(session: Session, date_strings: Dict[str, RepublicDate],
                             debug: int = 0) -> List[PhraseMatch]:
    date_matches = [match for match in session.evidence if match.has_label('session_date')]
    best_match = {}
    for dm in date_matches:
        dm_date = date_strings[dm.phrase.phrase_string]
        if dm.text_id in best_match:
            this_date_diff = session.date - dm_date
            best_date_diff = session.date - date_strings[best_match[dm.text_id].phrase.phrase_string]
            if this_date_diff.days < 0:
                continue
            if debug > 0:
                print(f"printed_session_parser.select_date_line_matches - diff between session.date and\n"
                      f"\tcurr date_match: {this_date_diff}"
                      f"\tbest date_match: {best_date_diff}")
            best_match[dm.text_id] = dm
        else:
            best_match[dm.text_id] = dm
    return [best_match[text_id] for text_id in best_match]


def map_session_starts_from_sessions(inventory_id: str, pages: List[pdm.PageXMLPage],
                                     sessions: List[Session], inv_metadata: Dict[str, any] = None,
                                     debug: int = 0) -> List[Dict[str, any]]:
    if inv_metadata is None:
        inv_metadata = get_inventory_by_id(inventory_id)
    sorted_pages = sorted(pages, key=lambda p: p.id)
    date_mapper = get_date_mapper(inv_metadata, sorted_pages, debug=0)
    current_date = initialize_inventory_date(inv_metadata, date_mapper)
    # print(inventory_id, current_date)
    date_strings = get_next_date_strings(current_date, num_dates=366, include_year=False, date_mapper=date_mapper)
    # print('date_strings:', date_strings.keys())
    session_starts = []
    for si, session in enumerate(sessions):
        found_date_lines = []
        date_matches = select_date_line_matches(session, date_strings)
        for match in date_matches:
            if 'session_date' not in match.label:
                continue
            if debug > 0:
                print(match.label[0], match.string, match.text_id)
            found_date = date_strings[match.phrase.phrase_string]
            if match.text_id in found_date_lines:
                print('WARNING - date line already encountered:', si, match.text_id, match.phrase.phrase_string)
                continue
            found_date_lines.append(match.text_id)
            date_scan = match.text_id.split('-line-')[0]
            if re.search(r"NL-HaNA_1\.(01|10)\.(02|94)_\d{4}\w?_\d{4}$", date_scan) is False:
                raise ValueError(f"unexpected line ID format for line {match.text_id}")
            session_start = {
                'inventory_num': inv_metadata['inventory_num'],
                'inventory_id': inventory_id,
                'session_date': session.date.isoformat(),
                'date': found_date.isoformat(),
                'date_line': match.text_id,
                'date_scan': match.text_id.split('-line-')[0],
                'date_string': match.phrase.phrase_string
            }
            session_starts.append(session_start)
    return session_starts


def map_session_lines_from_session_starts(inventory_id: str, pages: List[pdm.PageXMLPage],
                                          session_starts: List[Dict[str, any]],
                                          inv_metadata: Dict[str, any] = None,
                                          debug: int = 0):
    if inv_metadata is None:
        inv_metadata = get_inventory_by_id(inventory_id)
    sorted_pages = sorted(pages, key=lambda p: p.id)

    start_iterator = make_start_iterator(session_starts)
    next_start = start_iterator()
    next_start_date = make_republic_date(next_start['date'])

    date_mapper = get_date_mapper(inv_metadata, sorted_pages, debug=debug)

    prev_date = make_republic_date(inv_metadata['period_start']) - datetime.timedelta(days=1)
    current_date = initialize_inventory_date(inv_metadata, date_mapper)
    first_date = current_date.isoformat()
    if current_date > next_start_date:
        first_date = next_start['date']

    date_strings = get_next_date_strings(prev_date, num_dates=366, include_year=False, date_mapper=date_mapper)

    if next_start is not None and next_start['date'] > current_date.isoformat():
        if debug > 0:
            print('map_session_lines_from_session_starts - next_start date is not initial date:', current_date.isoformat())
        current_date = date_strings[next_start['date_string']]
    elif next_start is None:
        if debug > 0:
            print('map_session_lines_from_session_starts - next_start date is not initial date:', current_date.isoformat())
        while current_date.is_rest_day() and (next_start is None or current_date.isoformat() < next_start['date']):
            if debug > 0:
                print('map_session_lines_from_session_starts - REST DAY:', current_date.isoformat())
            current_date = get_next_workday(current_date, debug=debug)
        if debug > 0:
            print('map_session_lines_from_session_starts - CURRENT DAY:', current_date.isoformat())

    inv_id = inv_metadata['inventory_id']
    if debug > 0:
        print('map_session_lines_from_session_starts - first next_start:', next_start['date'])

    session_lines = []
    session_lines_map = {}
    stream_line_count = 0

    start_lines = [ss['date_line'] for ss in session_starts]

    start_lines_set = set(start_lines)
    repetition_dates = [date for date in exception_dates if 'repetition' in exception_dates[date]]
    mistake_dates = [date for date in exception_dates if 'mistake' in exception_dates[date]]
    if debug > 0:
        print('printed_session_parser.map_session_lines_from_session_starts - repetition_dates:', repetition_dates)
        print('printed_session_parser.map_session_lines_from_session_starts - mistake_dates:', mistake_dates)
        print('a')
    exception_session_dates = set()
    exception_multi = 0
    accept_double = set()

    for li, line in enumerate(stream_resolution_page_lines(inv_id, sorted_pages)):
        if debug > 2 and (li+1) % 1000 == 0:
            print(f"line {li+1} - {line.id}: {line.text}")
        stream_line_count += 1
        if debug > 2:
            if next_start and line.id == next_start['date_line']:
                print(f"line {li+1}: dates in session_lines_map: {session_lines_map.keys()}")
                print()
        if next_start is None and line.id in start_lines_set:
            print(f"printed_session_parser.map_session_lines_from_session_starts\n"
                  f"\tline {line.id} is session start but next_start is None")
        if next_start is not None and line.id == next_start['date_line']:
            if current_date.isoformat() in session_lines_map:
                if debug > 0:
                    print(f"printed_session_parser.map_session_lines_from_session_starts\n"
                          f"\tnext_start {next_start['date']}\n"
                          f"\tcurrent_date {current_date.isoformat()} already in session_lines_map")
                if current_date.isoformat() in exception_session_dates:
                    if debug > 0:
                        print(f"printed_session_parser.map_session_lines_from_session_starts\n"
                              f"\tmulti, date in exception_session_dates {current_date.isoformat()}")
                    exception_multi += 1
                elif current_date.isoformat() in repetition_dates:
                    if debug > 0:
                        print(f"printed_session_parser.map_session_lines_from_session_starts\n"
                              f"\tmulti, date in repetition_dates for {current_date.isoformat()}")
                    accept_double.add(current_date.isoformat())
                    repetition_dates.remove(current_date.isoformat())
                    exception_multi += 1
                elif len(session_lines) < 10 and len(session_lines_map[current_date.isoformat()]) < 10:
                    if debug > 0:
                        print(f"printed_session_parser.map_session_lines_from_session_starts\n"
                              f"\tmulti, short sessions for {current_date.isoformat()}")
                        print(f"\t{len(session_lines)} and {len(session_lines_map[current_date.isoformat()])}")
                    exception_multi += 1
                elif len(session_lines_map) < 2:
                    if debug > 0:
                        print(f"printed_session_parser.map_session_lines_from_session_starts\n"
                              f"\tmulti, first sessions for {current_date.isoformat()}")
                        print(f"\t{len(session_lines)} and {len(session_lines_map[current_date.isoformat()])} lines")
                    exception_multi += 1
                elif current_date.isoformat() in accept_double:
                    # for the second time a repetition date is encountered
                    if debug > 0:
                        print(f"printed_session_parser.map_session_lines_from_session_starts\n"
                              f"\tmulti, date in accept_double for {current_date.isoformat()}")
                    accept_double.remove(current_date.isoformat())
                else:
                    if debug > 0:
                        print(f"printed_session_parser.map_session_lines_from_session_starts\n"
                              f"\tmulti, not in exceptions {current_date.isoformat()} already in session_lines_map")
                        print(f"\t", next_start)
                if debug > 0:
                    print(f"printed_session_parser.map_session_lines_from_session_starts\n"
                          f"\tadding {len(session_lines)} lines to current date {current_date.isoformat()}")
                session_lines_map[current_date.isoformat()].extend(session_lines)
            else:
                if debug > 1:
                    print(f"printed_session_parser.map_session_lines_from_session_starts\n"
                          f"\tadding {len(session_lines)} lines to current date {current_date.isoformat()}")
                if len(session_lines_map) == 0:
                    print(f"printed_session_parser.map_session_lines_from_session_starts - "
                          f"Adding first lines to first date {first_date}")
                    session_lines_map[first_date] = session_lines
                else:
                    if debug > 1:
                        print(f"printed_session_parser.map_session_lines_from_session_starts - "
                              f"next_starts is None, adding lines to current date {current_date.isoformat()}")
                    session_lines_map[current_date.isoformat()] = session_lines
            session_lines = []
            if debug > 1:
                print(f"printed_session_parser.map_session_lines_from_session_starts - "
                      f"line number {li} line.id: {line.id}\ttext: {line.text}")
            # Reasoning behind setting the date:
            # - if no date string was found in the session start detection, assume the date
            #    assigned to the session is correct
            # - if a date string was found and it is not the same as the session date, and it
            #    is a rest day, assume it was found as a nihil actum and use the found date string
            #    Example: Dominica den 13 September which is attached to Luna den 14 September
            # - if a date string was found and it is not the same as the session date, and it
            #    is NOT a rest day, assume it is a date exception (see the list of date exceptions
            #    in republic.model.republic_date.pyp) and use the session date.
            #    Example: Martis den 12 September (the 12th of September was a Saturday and the
            #    week day Martis was printed by mistake.)
            # - if a date string was found and it is the same as the session date, assume it is
            #   correct and use the found date.
            if next_start['date_string'] is None:
                if debug > 1:
                    print(f"\tupdating current date to next_start['date'] {next_start['date']}")
                current_date = RepublicDate(date_string=next_start['date'])
                exception_session_dates.add(current_date.isoformat())
                if debug > 1:
                    print(f"\tdate_string is None, use session.date {next_start['session_date']}")
            elif next_start['date'] != next_start['session_date']:
                if date_strings[next_start['date_string']].is_rest_day():
                    if debug > 1:
                        print(f"\tupdating current date to next_start['date_string'] {next_start['date_string']}")
                    current_date = date_strings[next_start['date_string']]
                    exception_session_dates.add(current_date.isoformat())
                    if debug > 0:
                        print(f"\tdate {next_start['date']} is not session_date {next_start['session_date']}"
                              f" and is a rest day, use date {next_start['date']}")
                else:
                    # probably a date exception, see above
                    if debug > 0:
                        print(f"\tdate {next_start['date']} is not session_date {next_start['session_date']}"
                              f" and is not a rest day, use session_date {next_start['session_date']}")
                        print(f"\tupdating current date to next_start['session_date'] {next_start['session_date']}")
                    current_date = RepublicDate(date_string=next_start['session_date'])
                    exception_session_dates.add(current_date.isoformat())
            else:
                if debug > 1:
                    print(f"\tdate {next_start['date']} is session_date {next_start['session_date']}"
                          f", use session_date {next_start['session_date']}")
                if debug > 1:
                    print(f"\tupdating current date to next_start['session_date'] {next_start['session_date']}")
                current_date = RepublicDate(date_string=next_start['session_date'])
                # current_date = date_strings[next_start['date_string']]
            next_start = start_iterator()
            if debug > 1:
                if next_start is not None:
                    print(f"\nprinted_session_parser.map_session_lines_from_session_starts - next_start:"
                          f"\n\tsession_date {next_start['session_date']}\n\tdate {next_start['date']}"
                          f"\n\tdate_string {next_start['date_string']}"
                          f"\n\tdate_strings(date_string): {date_strings[next_start['date_string']]}"
                          f"\n\tis_rest_day: {date_strings[next_start['date_string']].is_rest_day()}"
                          f"\n\tcurrent_date: {current_date.isoformat()}"
                          )
                    print()
                else:
                    print('printed_session_parser.map_session_lines_from_session_starts - next_start:', next_start)
        session_lines.append(line)
    if current_date.isoformat() in session_lines_map:
        if debug > 0:
            print(f"printed_session_parser.map_session_lines_from_session_starts\n"
                  f"\tcurrent_date {current_date.isoformat()} already in session_lines_map")
        session_lines_map[current_date.isoformat()].extend(session_lines)
    else:
        session_lines_map[current_date.isoformat()] = session_lines
    map_line_count = sum([len(session_lines_map[session_date]) for session_date in session_lines_map])

    if map_line_count != stream_line_count:
        raise ValueError(f"map_line_count {map_line_count} is not equal to stream_line_count {stream_line_count}")
    num_mapped = len(session_lines_map) + exception_multi
    # the number of mapped sessions can be 1 bigger than the number of session_starts
    # because the first session is not always identified as a start (because the title
    # lines on the title page mess up the columns
    if num_mapped < len(session_starts) or num_mapped > len(session_starts) + 1:
        print('printed_session_parser.map_session_lines_from_session_starts - number of '
              f'repeated exception dates: {exception_multi}')
        raise ValueError(f"number of mapped sessions {num_mapped} is not equal to "
                         f"the number of session starts {len(session_starts)}")

    return session_lines_map


def get_printed_sessions(inventory_id: str, pages: List[pdm.PageXMLPage],
                         session_starts: List[Dict[str, any]] = None,
                         inv_metadata: Dict[str, any] = None, start_date: str = None,
                         use_token_searcher: bool = False, start_page_idx: int = 0,
                         debug: int = 0, report_progress: bool = True) -> Generator[Session, None, None]:
    if session_starts is not None:
        print(f'printed_session_parser.get_printed_sessions - number of session_starts: {len(session_starts)}')
        session_gen = get_printed_sessions_from_session_starts(inventory_id, pages, session_starts,
                                                               inv_metadata=inv_metadata, start_date=start_date,
                                                               debug=debug)
    else:
        session_gen = get_printed_sessions_from_pages(inventory_id, pages, inv_metadata=inv_metadata,
                                                      use_token_searcher=use_token_searcher, start_date=start_date,
                                                      start_page_idx=start_page_idx, debug=debug,
                                                      report_progress=report_progress)
    for session in session_gen:
        yield session


def get_printed_sessions_from_session_starts(inventory_id: str, pages: List[pdm.PageXMLPage],
                                             session_starts: List[Dict[str, any]], inv_metadata: Dict[str, any] = None,
                                             start_date: str = None,
                                             debug: int = 0) -> Generator[Session, None, None]:
    if inv_metadata is None:
        inv_metadata = get_inventory_by_id(inventory_id)
    sorted_pages = sorted(pages, key=lambda p: p.id)
    date_mapper = get_date_mapper(inv_metadata, sorted_pages, debug=0)

    session_lines_map = map_session_lines_from_session_starts(inventory_id, pages, session_starts,
                                                              debug=debug)

    column_metadata = get_columns_metadata(sorted_pages)
    page_index = {page.id: page for page in sorted_pages}

    if start_date:
        current_date = RepublicDate(date_string=start_date)
    else:
        current_date = initialize_inventory_date(inv_metadata, date_mapper)
    if debug > 0:
        print('printed_session_parser.get_printed_sesions_from_mapped_lines - current_date:', current_date)

    session_searcher = SessionSearcher(inv_metadata, current_date,
                                       session_phrase_model, window_size=30,
                                       date_mapper=date_mapper, use_token_searcher=False)
    # session_meta, date_meta = session_searcher.parse_session_metadata(None, inv_metadata, [], debug=0)
    prev_meta = None
    for si, session_date in enumerate(session_lines_map):
        if debug > 0:
            print('printed_session_parser.get_printed_sesions_from_mapped_lines - session_date:', session_date)
        current_date = RepublicDate(date_string=session_date, date_mapper=date_mapper)

        # session_searcher = SessionSearcher(inv_metadata, current_date, session_phrase_model, window_size=30,
        #                                    date_mapper=date_mapper, use_token_searcher=False)
        session_searcher.sliding_window = []
        session_searcher.current_date = current_date
        for line in session_lines_map[session_date][:30]:
            if line.text is None or line.text == '':
                continue
            session_searcher.add_document(line.id, line.text, text_object=line, debug=0)

        session_searcher.get_session_opening_elements()
        session_meta, date_meta = session_searcher.parse_session_metadata(prev_meta, inv_metadata,
                                                                          session_lines_map[session_date],
                                                                          skip_rest_days=False, debug=0)
        session_doc = generate_session_doc(inv_metadata, session_meta, date_meta, session_lines_map[session_date],
                                           session_searcher, column_metadata, page_index)
        if debug > 2:
            print("printed_session_parser.generate_session_doc - doing quality control")
        check_session(session_doc)
        yield session_doc
        prev_meta = session_meta


def get_printed_sessions_from_pages(inventory_id: str, pages: List[pdm.PageXMLPage],
                                    inv_metadata: dict = None, start_date: str = None,
                                    use_token_searcher: bool = False, start_page_idx: int = 0,
                                    debug: int = 0, report_progress: bool = True) -> Iterator[Session]:
    # TO DO: IMPROVEMENTS
    # - check for large date jumps and short session docs
    if inv_metadata is None:
        inv_metadata = get_inventory_by_id(inventory_id)
    sorted_pages = sort_inventory_pages(inventory_id, pages)
    page_index = {page.id: page for page in sorted_pages}
    column_metadata = get_columns_metadata(sorted_pages)
    date_mapper = get_date_mapper(inv_metadata, sorted_pages, debug=debug)
    if debug > 2:
        print('printed_session_parser.get_printed_sessions - date_mapper:', date_mapper)
    if start_date:
        current_date = RepublicDate(date_string=start_date)
    else:
        current_date = initialize_inventory_date(inv_metadata, date_mapper)
    session_searcher = SessionSearcher(inv_metadata, current_date,
                                       session_phrase_model, window_size=30,
                                       date_mapper=date_mapper, use_token_searcher=use_token_searcher)
    session_lines: List[pdm.PageXMLTextLine] = []
    session_metadata, date_metadata = session_searcher.parse_session_metadata(None, inv_metadata, session_lines,
                                                                              debug=debug)
    gated_window = GatedWindow(window_size=10, open_threshold=500, shut_threshold=500)
    lines_skipped = 0
    print('printed_session_parser.get_printed_sessions - indexing start for current date:',
          current_date.isoformat())
    if debug > 0:
        print('printed_session_parser.get_printed_sessions - date_strings:', session_searcher.date_strings.keys())
    for li, line in enumerate(stream_resolution_page_lines(inventory_id, sorted_pages[start_page_idx:])):
        # before modifying, make sure we're working on a copy
        # remove all word-level objects, as we only need the text
        if debug > 3:
            print(f'printed_session_parser.get_printed_sessions - line {li}: {line.text}')
        line.words = []
        # list all lines belonging to the same session date
        session_lines += [line]
        if line.text is None or line.text == '':
            continue
        # add the line to the gated_window
        gated_window.add_line(line)
        if report_progress is True and (li+1) % 1000 == 0:
            print(f'{li+1} lines processed, {lines_skipped} lines skipped in fuzzy search')
        check_line = gated_window.get_first_doc()
        if not check_line:
            lines_skipped += 1
            # add a None to the sliding window as a placeholder so the sliding window keeps sliding
            session_searcher.add_empty_document()
            # print(li, None)
        else:
            # add the line as a new document to the session searcher and search for session elements
            session_searcher.add_document(check_line.id, check_line.text, text_object=line, debug=debug)
            if debug > 3:
                for model_name in session_searcher.phrase_models:
                    for phrase in session_searcher.phrase_models[model_name].phrase_index:
                        print('printed_session_parser.get_printed_sessions - phrase:', phrase)
                for phrase in session_searcher.phrases:
                    print(phrase)
            # print(li, check_line.text)
        # Keep sliding until the first line in the sliding window has matches
        # last_line = session_searcher.sliding_window[-1]
        if not session_searcher.sliding_window[0] or len(session_searcher.sliding_window[0]['matches']) == 0:
            continue
        # if not check_line:
        #     print(li - 40, None)
        # else:
        #     print(li - 40, check_line.text)
        # get the session opening elements found in the lines of the sliding window
        session_opening_elements = session_searcher.get_session_opening_elements()
        # print(session_opening_elements)
        # check if first session opening element is in the first line of the sliding window
        if len(session_opening_elements.items()) == 0 or min(session_opening_elements.values()) != 0:
            # move to next line if first session opening element is not in the first line of the sliding window
            continue
        # for window_line in session_searcher.sliding_window:
        #     print(window_line["text"])
        if 'extract' in session_opening_elements or 'insertion' in session_opening_elements:
            # what follows in the sliding window is an insertion of an external document, or an
            # extract from , which looks like a session opening but isn't. Reset the sliding window
            session_searcher.reset_sliding_window()
            continue
        if 'extract' in session_opening_elements or 'insertion' in session_opening_elements:
            print('DEBUG - pagexml_session_parser.get_sessions - extract phrase in session_opening_elements:')
            for line_doc in session_searcher.sliding_window:
                if not line_doc:
                    continue
                print('\t', line_doc['id'], line_doc['text'])
        # score the found session opening elements for how well
        # they match the order in which they are expected to appear
        # Empirically established threshold:
        # - need to match at least four session opening elements
        # - number of opening elements in expected order must be 99% of found opening elements
        if score_session_opening_elements(session_opening_elements, num_elements_threshold=4) > 0.99:
            if debug > 1:
                print('\nget_sessions - threshold reached - session_opening_elements:', session_opening_elements)
                for window_line in session_searcher.sliding_window:
                    if not window_line:
                        print(None)
                    else:
                        print(window_line['text'], [match.phrase for match in window_line['matches']])
                # print('\n')
            # get the first line of the new session day in the sliding window
            first_new_session_line_id = session_searcher.sliding_window[0]['id']
            # find that first line in the list of the collected session lines
            first_new_session_line = find_session_line(first_new_session_line_id, session_lines)
            # find the index of the first new session day line in the collected session lines
            new_session_index = session_lines.index(first_new_session_line)
            # everything before the first new session day line belongs to the previous day
            finished_session_lines = session_lines[:new_session_index]
            # everything after the first new session day line belongs to the new session day
            session_lines = session_lines[new_session_index:]
            session_doc = generate_session_doc(inv_metadata, session_metadata, date_metadata,
                                               finished_session_lines,
                                               session_searcher, column_metadata, page_index)
            # print('get_sessions - generated session_doc.metadata:', session_doc.metadata)
            # if session_doc.metadata['num_lines'] == 0:
            if session_doc.num_lines == 0:
                # A session with no lines only happens at the beginning
                # Don't generate a doc and set the already shifted date back by 1 day
                # Also, reset the session counter
                session_searcher.sessions[session_doc.metadata['session_date']] = []
                date = session_searcher.current_date
                if date.month == 1 and 1 < date.day <= 4:
                    # reset_date = RepublicDate(date.year, 1, 1)
                    day_shift = date.day - 1
                    session_searcher.update_session_date(day_shift)
            else:
                yield session_doc
            # update the current session date in the searcher
            session_searcher.update_session_date()
            # print('get_sessions - after update - current_date:', session_searcher.current_date)
            # update the searcher with new date strings for the next seven days
            session_searcher.update_session_date_searcher(num_dates=7)
            # get the session metadata for the new session date
            try:
                if debug > 0:
                    first_page_id = session_lines[0].metadata['page_id']
                    page_idx = None
                    for pi, page in enumerate(sorted_pages):
                        if page.id == first_page_id:
                            page_idx = pi
                    print(f'printed_session_parser.get_printed_sessions - page idx of first line',
                          page_idx, first_page_id)
                session_metadata, date_metadata = session_searcher.parse_session_metadata(session_doc.metadata,
                                                                                          inv_metadata,
                                                                                          session_lines,
                                                                                          debug=debug)
            except Exception as err:
                debug_prefix = 'printed_session_parser.get_printed_sessions - '
                print(f'{debug_prefix}Error parsing session metadata for session {session_doc.id}')
                print(f'{debug_prefix}first session line: {session_lines[0].id}')
                print(f'{debug_prefix}last session line: {session_lines[-1].id}')
                print(err)
                raise
            # reset the sliding window to search the next session opening
            session_searcher.shift_sliding_window()
    session_metadata['num_lines'] = len(session_lines)
    # after processing all lines in the inventory, create a session doc from the remaining lines
    yield generate_session_doc(inv_metadata, session_metadata, date_metadata,
                               session_lines, session_searcher, column_metadata, page_index)


def get_session_scans_version(session: Session) -> List:
    scans_version = {}
    for line in session.lines:
        scans_version[line.metadata['doc_id']] = copy.copy(line.metadata['scan_version'])
        scans_version[line.metadata['doc_id']]['doc_id'] = line.metadata['doc_id']
    # print("session scans versions:", scans_version)
    return list(scans_version.values())


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
        missing_session.scan_versions = get_session_scans_version(missing_session)
        clean_lines(missing_session.lines, clean_copy=False)
        print('missing session:', missing_session.id)
        yield missing_session
