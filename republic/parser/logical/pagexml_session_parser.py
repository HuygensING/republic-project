from typing import List, Dict, Generator, Union, Iterator
from collections import defaultdict
import copy

from republic.model.physical_document_model import PageXMLPage, PageXMLTextLine, PageXMLTextRegion
from republic.model.physical_document_model import parse_derived_coords
from republic.model.republic_phrase_model import session_phrase_model
from republic.model.republic_date import RepublicDate, derive_date_from_string
from republic.model.republic_session import SessionSearcher, calculate_work_day_shift
from republic.model.republic_session import session_opening_element_order
from republic.model.republic_document_model import Session
from republic.helper.pagexml_helper import sort_lines_in_reading_order


def initialize_inventory_date(inv_metadata: dict) -> RepublicDate:
    year, month, day = [int(part) for part in inv_metadata['period_start'].split('-')]
    return RepublicDate(year, month, day)


def stream_resolution_page_lines(pages: List[PageXMLPage]) -> Generator[PageXMLTextLine, None, None]:
    """Iterate over list of pages and return a generator that yields individuals lines.
    Iterator iterates over columns and textregions.
    Assumption: lines are returned in reading order."""
    pages = sorted(pages, key=lambda x: x.metadata['page_num'])
    for page in pages:
        if not page.columns:
            continue
        for line in sort_lines_in_reading_order(page):
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


def find_session_line(line_id: str, session_lines: List[PageXMLTextLine]) -> PageXMLTextLine:
    """Find a specific line by id in the list of lines belonging to a session."""
    for line in session_lines:
        if line.id == line_id:
            return line
    raise IndexError(f'Line with id {line_id} not in session lines.')


def generate_session_doc(session_metadata: dict, session_lines: List[PageXMLTextLine],
                         session_searcher: SessionSearcher, column_metadata: Dict[str, dict]) -> iter:
    evidence = session_metadata['evidence']
    del session_metadata['evidence']
    text_region_lines = defaultdict(list)
    text_regions: List[PageXMLTextRegion] = []
    scan_version = {}
    session_text_page_nums = set()
    for line in session_lines:
        text_region_id = line.metadata['column_id']
        text_region_lines[text_region_id].append(line)
    for text_region_id in text_region_lines:
        metadata = column_metadata[text_region_id]
        coords = parse_derived_coords(text_region_lines[text_region_id])
        text_region = PageXMLTextRegion(doc_id=text_region_id, metadata=metadata,
                                        coords=coords, lines=text_region_lines[text_region_id])
        # We're going from physical to logical structure here, so add a trace to the
        # logical structure elements about where they come from in the physical
        # structure, especially the printed page number needed for linking to locators
        # in the index pages.
        source_page = text_region_lines[text_region_id][0].parent.parent
        scan_version[source_page.metadata['scan_id']] = source_page.metadata['textrepo_version']
        text_region.metadata['page_id'] = source_page.id
        text_region.metadata['page_num'] = source_page.metadata['page_num']
        text_region.metadata['text_page_num'] = source_page.metadata['text_page_num']
        if isinstance(source_page.metadata["text_page_num"], int):
            session_text_page_nums.add(source_page.metadata['text_page_num'])
        text_regions.append(text_region)
    for scan_id in scan_version:
        scan_version[scan_id]['scan_id'] = scan_id
    session = Session(metadata=session_metadata, text_regions=text_regions,
                      evidence=evidence, scan_versions=list(scan_version.values()))
    session.metadata["text_page_num"] = sorted(list(session_text_page_nums))
    # session.add_page_text_region_metadata(column_metadata)
    # add number of lines to session info in session searcher
    session_info = session_searcher.sessions[session_metadata['session_date']][-1]
    session_info['num_lines'] = len(session_lines)
    # print('this sessions contains elements from the following scans:', session.scan_versions)
    if session.date.is_rest_day() or not session_searcher.has_session_date_match():
        return session
    # Check if the next session date is more than 1 workday ahead
    date_match = session_searcher.get_session_date_match()
    new_date = derive_date_from_string(date_match.phrase.phrase_string, session_searcher.year)
    if session.date.isoformat() == new_date.isoformat():
        # print('SAME DAY:', session_searcher.current_date.isoformat(), '\t', session.date.isoformat())
        return session
    workday_shift = calculate_work_day_shift(new_date, session.date)
    # print('workday_shift:', workday_shift)
    if workday_shift > 1:
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
        self.sliding_window: List[Union[None, PageXMLTextLine]] = [None] * window_size
        self.open_threshold = open_threshold
        self.shut_threshold = shut_threshold
        self.gate_open = False
        self.num_chars = 0
        self.let_through: List[bool] = [False] * window_size

    def add_line(self, line: PageXMLTextLine):
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

    def get_first_doc(self) -> Union[None, PageXMLTextLine]:
        """Return the first sentence in the sliding window if it is set to be let through, otherwise return None."""
        return self.sliding_window[0] if self.let_through[0] else None


def get_columns_metadata(sorted_pages: List[PageXMLPage]) -> Dict[str, dict]:
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
            column_metadata['textrepo_version'] = page.metadata['textrepo_version']
    return column_metadata


def get_sessions(sorted_pages: List[PageXMLPage], inv_num: int,
                 inv_metadata: dict) -> Iterator[Session]:
    # TO DO: IMPROVEMENTS
    # - check for large date jumps and short session docs
    column_metadata = get_columns_metadata(sorted_pages)
    current_date = initialize_inventory_date(inv_metadata)
    session_searcher = SessionSearcher(inv_num, current_date,
                                       session_phrase_model, window_size=30)
    session_metadata = session_searcher.parse_session_metadata(None)
    gated_window = GatedWindow(window_size=10, open_threshold=400, shut_threshold=400)
    lines_skipped = 0
    print('indexing start for current date:', current_date.isoformat())
    session_lines: List[PageXMLTextLine] = []
    for li, line in enumerate(stream_resolution_page_lines(sorted_pages)):
        # before modifying, make sure we're working on a copy
        # remove all word-level objects, as we only need the text
        line.words = []
        # list all lines belonging to the same session date
        session_lines += [line]
        if line.text is None or line.text == '':
            continue
        # add the line to the gated_window
        gated_window.add_line(line)
        if (li+1) % 1000 == 0:
            print(f'{li+1} lines processed, {lines_skipped} lines skipped in fuzzy search')
        check_line = gated_window.get_first_doc()
        if not check_line:
            lines_skipped += 1
            # add a None to the sliding window as a placeholder so the sliding window keeps sliding
            session_searcher.add_empty_document()
            # print(li, None)
        else:
            # add the line as a new document to the session searcher and search for session elements
            session_searcher.add_document(check_line.id, check_line.text, text_object=line)
            # print(li, check_line.text)
        # Keep sliding until the first line in the sliding window has matches
        # last_line = session_searcher.sliding_window[-1]
        # if not last_line:
        #     print(None)
        # else:
        #     print(li - 40, last_line['text_string'], [match['match_string'] for match in last_line['matches']])
        if not session_searcher.sliding_window[0] or len(session_searcher.sliding_window[0]['matches']) == 0:
            continue
        # get the session opening elements found in the lines of the sliding window
        session_opening_elements = session_searcher.get_session_opening_elements()
        # print(session_opening_elements)
        # check if first session opening element is in the first line of the sliding window
        if len(session_opening_elements.items()) == 0 or min(session_opening_elements.values()) != 0:
            # move to next line if first session opening element is not in the first line of the sliding window
            continue
        if 'extract' in session_opening_elements:
            # what follows in the sliding window is an extract from earlier days, which looks
            # like a session opening but isn't. Reset the sliding window
            session_searcher.reset_sliding_window()
            continue
        if 'extract' in session_opening_elements:
            for line_doc in session_searcher.sliding_window:
                if not line_doc:
                    continue
                print(line_doc['id'], line_doc['text'])
        # score the found session opening elements for how well
        # they match the order in which they are expected to appear
        # Empirically established threshold:
        # - need to match at least four session opening elements
        # - number of opening elements in expected order must be 99% of found opening elements
        if score_session_opening_elements(session_opening_elements, num_elements_threshold=4) > 0.99:
            # for line in session_searcher.sliding_window:
            #     if not line:
            #         print(None)
            #     else:
            #         print(line['text_string'], [match['match_keyword'] for match in line['matches']])
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
            session_doc = generate_session_doc(session_metadata, finished_session_lines,
                                               session_searcher, column_metadata)
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
            # update the searcher with new date strings for the next seven days
            session_searcher.update_session_date_searcher(num_dates=7)
            # get the session metadata for the new session date
            session_metadata = session_searcher.parse_session_metadata(session_doc.metadata)
            # reset the sliding window to search the next session opening
            session_searcher.shift_sliding_window()
    session_metadata['num_lines'] = len(session_lines)
    # after processing all lines in the inventory, create a session doc from the remaining lines
    yield generate_session_doc(session_metadata, session_lines, session_searcher, column_metadata)


def get_session_scans_version(session: Session) -> List:
    scans_version = {}
    for line in session.lines:
        scans_version[line.metadata['doc_id']] = copy.copy(line.metadata['scan_version'])
        scans_version[line.metadata['doc_id']]['doc_id'] = line.metadata['doc_id']
    # print("session scans versions:", scans_version)
    return list(scans_version.values())
