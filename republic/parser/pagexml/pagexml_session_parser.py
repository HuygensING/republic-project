from typing import List, Dict, Union, Iterator
from collections import Counter
import copy

from republic.model.physical_document_model import StructureDoc
from republic.model.republic_phrase_model import session_phrase_model
from republic.model.republic_date import RepublicDate, derive_date_from_string
from republic.model.republic_session import SessionSearcher, calculate_work_day_shift
from republic.model.republic_session import session_opening_element_order
from republic.model.republic_document_model import Session, ResolutionPageDoc
from republic.model.republic_document_model import check_special_column_for_bleed_through, sort_resolution_columns
from republic.helper.text_helper import read_word_freq_counter


def initialize_inventory_date(inv_metadata: dict) -> RepublicDate:
    year, month, day = [int(part) for part in inv_metadata['period_start'].split('-')]
    return RepublicDate(year, month, day)


def get_vertical_overlap(line1: dict, line2: dict) -> int:
    top = max(line1['coords']['top'], line2['coords']['top'])
    bottom = min(line1['coords']['bottom'], line2['coords']['bottom'])
    return bottom - top if bottom > top else 0


def get_horizontal_overlap(line1: dict, line2: dict) -> int:
    left = max(line1['coords']['left'], line2['coords']['left'])
    right = min(line1['coords']['right'], line2['coords']['right'])
    return right - left if right > left else 0


def merge_aligned_lines(lines: list) -> list:
    aligned_lines = []
    prev_line = None
    for li, line in enumerate(lines):
        line = copy.copy(line)
        if not line['text']:
            continue
        vertical_overlap, horizontal_overlap = 0, 0
        if prev_line:
            vertical_overlap = get_vertical_overlap(prev_line, line)
            horizontal_overlap = get_horizontal_overlap(prev_line, line)
        if vertical_overlap / line['coords']['height'] < 0.75:
            aligned_lines += [line]
        elif horizontal_overlap / 10:
            aligned_lines += [line]
        elif line['coords']['left'] < aligned_lines[-1]['coords']['left']:
            aligned_lines[-1]['text'] = line['text'] + ' ' + aligned_lines[-1]['text']
        else:
            aligned_lines[-1]['text'] += ' ' + line['text']
        prev_line = line
    return aligned_lines


def swap_lines(line1: dict, line2: dict):
    if line2 is None:
        # line2 is not a line, so no swap
        return False
    if line1["coords"]["right"] < line2["coords"]["left"]:
        # line2 is to the right of line1, so no swap
        return False
    if line1["coords"]["bottom"] < line2["coords"]["top"] + 10:
        # line2 is below line1, so no swap
        return False
    if line2["coords"]["bottom"] < line1["coords"]["top"] + 10:
        # line2 is entirely above line1, so swap
        return True
    if line1["left_alignment"] == "column":
        # lines have horizontal overlap, but line 1 is left aligned
        return False
    if line1["coords"]["left"] < line2["coords"]["right"] - 10:
        # line 1 has too much overlap with line 2
        return False
    else:
        return True


def order_document_lines(document: ResolutionPageDoc):
    lines = [line for line in stream_resolution_document_lines([document])
             if line is not None and line["text"] is not None]
    ordered_lines = []
    for li, line in enumerate(lines):
        if line in ordered_lines:
            continue
        next_line = lines[li + 1] if li < len(lines) - 1 else None
        if swap_lines(line, next_line):
            ordered_lines.append(next_line)
        ordered_lines.append(line)


def stream_resolution_page_lines(pages: List[ResolutionPageDoc],
                                 word_freq_counter: Counter = None) -> Union[None, iter]:
    """Iterate over list of pages and return a generator that yields individuals lines.
    Iterator iterates over columns and textregions.
    Assumption: lines are returned in reading order."""
    pages = sorted(pages, key=lambda x: x.metadata['page_num'])
    for page in pages:
        if 'scan_id' not in page.metadata:
            page.metadata['scan_id'] = page.metadata['id'].split('-page')[0]
    return stream_resolution_document_lines(pages, word_freq_counter=word_freq_counter)


def line_add_document_metadata(line: dict, document: ResolutionPageDoc):
    # line['inventory_num'] = document.metadata['inventory_num']
    line['metadata']['scan_id'] = document.metadata['scan_id']
    line['metadata']['scan_num'] = document.metadata['scan_num']
    line['metadata']['doc_id'] = document.metadata['id']
    # line['page_num'] = document.metadata['page_num']
    # line['column_index'] = ci
    line['metadata']['column_id'] = line['metadata']['id'].split('-tr-')[0]
    # line['textregion_index'] = ti
    line['metadata']['textregion_id'] = line['metadata']['id'].split('-line-')[0]
    line['metadata']['line_index'] = int(line['metadata']['id'].split('-line-')[1])
    line['metadata']['scan_version'] = document.scan_version
    return line


def stream_resolution_document_lines(documents: List[ResolutionPageDoc],
                                     word_freq_counter: Counter = None) -> Union[None, iter]:
    """Iterate over list of documents and return a generator that yields individuals lines.
    Iterator iterates over columns and textregions.
    Assumption: lines are returned in reading order."""
    for document in documents:
        if word_freq_counter:
            for column in document.columns:
                check_special_column_for_bleed_through(column, word_freq_counter)
        try:
            columns = sort_resolution_columns(document.columns)
        except KeyError:
            print(document.metadata['id'])
            raise
        for ci, column in columns:
            # print('column id:', column['metadata']['id'])
            # print('column coords:', column['coords'])
            lines = []
            for ti, textregion in enumerate(column['textregions']):
                # print('textregion coords:', textregion['coords'])
                if 'lines' not in textregion or not textregion['lines']:
                    continue
                for li, line in enumerate(textregion['lines']):
                    line = line_add_document_metadata(line, document)
                    lines += [line]
            # sort lines to make sure they are in reading order (assuming column has single text column)
            # some columns split their text in sub columns, but for session date detection this is not an issue
            for line in sorted(lines, key=lambda x: x['coords']['bottom']):
                yield line
    return None


def print_line_info(line_info: dict) -> None:
    print('\t', line_info['page_num'], line_info['column_index'],
          line_info['metadata']['textregion_index'], line_info['line_index'],
          line_info['coords']['top'], line_info['coords']['bottom'],
          line_info['coords']['left'], line_info['coords']['right'],
          line_info['text'])


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


def find_session_line(line_id: str, session_lines: List[dict]) -> dict:
    """Find a specific line by id in the list of lines belonging to a session."""
    for line in session_lines:
        if line['metadata']['id'] == line_id:
            return line
    raise IndexError(f'Line with id {line_id} not in session lines.')


def generate_session_doc(session_metadata: dict, session_lines: list,
                         session_searcher: SessionSearcher, column_metadata: Dict[str, dict]) -> iter:
    evidence = session_metadata['evidence']
    del session_metadata['evidence']
    session = Session(session_metadata, lines=session_lines, evidence=evidence)
    session.add_page_column_metadata(column_metadata)
    # add number of lines to session info in session searcher
    session_info = session_searcher.sessions[session_metadata['session_date']][-1]
    session_info['num_lines'] = len(session_lines)
    if session.date.is_rest_day() or not session_searcher.has_session_date_match():
        return session
    # Check if the next session date is more than 1 workday ahead
    date_match = session_searcher.get_session_date_match()
    new_date = derive_date_from_string(date_match['match_keyword'], session_searcher.year)
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
        self.sliding_window: List[Union[None, Dict[str, Union[str, int, Dict[str, int]]]]] = [None] * window_size
        self.open_threshold = open_threshold
        self.shut_threshold = shut_threshold
        self.gate_open = False
        self.num_chars = 0
        self.let_through: List[bool] = [False] * window_size

    def add_doc(self, doc: Dict[str, Union[str, int, Dict[str, int]]]):
        """Add a document to the sliding window. doc should be a dictionary with
        the 'text' property containing the document text."""
        if len(self.sliding_window) >= self.window_size:
            self.sliding_window = self.sliding_window[-self.window_size+1:]
            self.let_through = self.let_through[-self.window_size+1:]
        self.let_through += [False]
        self.sliding_window += [doc]
        self.check_treshold()

    def num_chars_in_window(self) -> int:
        """Return the number of characters in the sliding window documents."""
        return sum([len(doc['text']) for doc in self.sliding_window if doc])

    def check_treshold(self) -> None:
        """Check whether the number of characters in the sliding window crosses
        the current threshold and set let_through accordingly."""
        if self.sliding_window[self.middle_doc] is None:
            # If the sliding window is not filled yet, the middle doc is not let through
            pass
        elif self.num_chars_in_window() < self.shut_threshold:
            self.let_through[self.middle_doc] = True

    def get_first_doc(self) -> Dict[str, Union[str, int, Dict[str, int]]]:
        """Return the first sentence in the sliding window if it is set to be let through, otherwise return None."""
        return self.sliding_window[0] if self.let_through[0] else None


def get_columns_metadata(sorted_pages: List[Union[StructureDoc, dict]]) -> Dict[str, dict]:
    column_metadata = {}
    for page in sorted_pages:
        columns = page.columns if isinstance(page, StructureDoc) else page['columns']
        for column in columns:
            column_id = column['metadata']['id']
            column_metadata[column_id] = copy.deepcopy(column['metadata'])
    return column_metadata


def get_sessions(sorted_pages: List[ResolutionPageDoc], inv_config: dict,
                 inv_metadata: dict) -> Iterator[Session]:
    # TO DO: IMPROVEMENTS
    # - add holidays: Easter, Christmas
    # - make model year-dependent
    # - check for large date jumps and short session docs
    column_metadata = get_columns_metadata(sorted_pages)
    current_date = initialize_inventory_date(inv_metadata)
    session_searcher = SessionSearcher(inv_config['inventory_num'], current_date,
                                       session_phrase_model, window_size=30)
    session_metadata = session_searcher.parse_session_metadata(None)
    gated_window = GatedWindow(window_size=10, open_threshold=400, shut_threshold=400)
    lines_skipped = 0
    print('indexing start for current date:', current_date.isoformat())
    session_lines = []
    word_freq_counter = read_word_freq_counter(inv_config, 'line')
    for li, line_info in enumerate(stream_resolution_page_lines(sorted_pages,
                                                                word_freq_counter=word_freq_counter)):
        # list all lines belonging to the same session date
        session_lines += [line_info]
        if line_info['text'] is None or line_info['text'] == '':
            continue
        # add the line to the gated_window
        gated_window.add_doc(line_info)
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
            session_searcher.add_document(check_line['metadata']['id'], check_line['text'])
            # print(li, check_line['text'])
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
            for line in session_searcher.sliding_window:
                if not line:
                    continue
                print(line['metadata']['text_id'], line['text_string'])
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
            first_new_session_line_id = session_searcher.sliding_window[0]['text_id']
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
            if session_doc.metadata['num_lines'] == 0:
                # A session with no lines only happens at the beginning
                # Don't generate a doc and sets the already shifted date back by 1 day
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
