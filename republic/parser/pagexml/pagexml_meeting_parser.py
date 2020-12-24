from typing import List, Dict, Union, Iterator
from collections import Counter
import copy

from republic.model.republic_phrase_model import meeting_phrase_model
from republic.model.republic_date import RepublicDate, derive_date_from_string, exception_dates
# print(exception_dates)
from republic.model.republic_meeting import MeetingSearcher, Meeting, calculate_work_day_shift
from republic.model.republic_meeting import meeting_element_order
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


def order_document_lines(document: dict):
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


def stream_resolution_page_lines(pages: list, word_freq_counter: Counter = None) -> Union[None, iter]:
    """Iterate over list of pages and return a generator that yields individuals lines.
    Iterator iterates over columns and textregions.
    Assumption: lines are returned in reading order."""
    pages = sorted(pages, key=lambda x: x['metadata']['page_num'])
    for page in pages:
        if 'scan_id' not in page['metadata']:
            page['metadata']['scan_id'] = page['metadata']['id'].split('-page')[0]
    return stream_resolution_document_lines(pages, word_freq_counter=word_freq_counter)


def line_add_document_metadata(line: dict, document: Dict[str, any]):
    # line['inventory_num'] = document['metadata']['inventory_num']
    line['metadata']['scan_id'] = document['metadata']['scan_id']
    line['metadata']['scan_num'] = document['metadata']['scan_num']
    line['metadata']['doc_id'] = document['metadata']['id']
    # line['page_num'] = document['metadata']['page_num']
    # line['column_index'] = ci
    line['metadata']['column_id'] = line['metadata']['id'].split('-tr-')[0]
    # line['textregion_index'] = ti
    line['metadata']['textregion_id'] = line['metadata']['id'].split('-line-')[0]
    line['metadata']['line_index'] = int(line['metadata']['id'].split('-line-')[1])
    line['metadata']['scan_version'] = document["version"]
    return line


def stream_resolution_document_lines(documents: List[dict],
                                     word_freq_counter: Counter = None) -> Union[None, iter]:
    """Iterate over list of documents and return a generator that yields individuals lines.
    Iterator iterates over columns and textregions.
    Assumption: lines are returned in reading order."""
    for document in documents:
        if word_freq_counter:
            for column in document['columns']:
                check_special_column_for_bleed_through(column, word_freq_counter)
        try:
            columns = sort_resolution_columns(document['columns'])
        except KeyError:
            print(document['metadata']['id'])
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
            # some columns split their text in sub columns, but for meeting date detection this is not an issue
            for line in sorted(lines, key=lambda x: x['coords']['bottom']):
                yield line
    return None


def print_line_info(line_info: dict) -> None:
    print('\t', line_info['page_num'], line_info['column_index'],
          line_info['metadata']['textregion_index'], line_info['line_index'],
          line_info['coords']['top'], line_info['coords']['bottom'],
          line_info['coords']['left'], line_info['coords']['right'],
          line_info['text'])


def score_meeting_elements(meeting_elements: Dict[str, int], num_elements_threshold: int) -> float:
    """Order meeting elements by text order and check against expected order. If enough elements are
    in expected order, the number of ordered elements is returned as the score, otherwise score is zero."""
    elements = sorted(meeting_elements.items(), key=lambda x: x[1])
    if len(meeting_elements.keys()) < num_elements_threshold:
        # we need at least num_elements_threshold elements to determine this is a new meeting date
        return 0
    try:
        numbered_elements = [meeting_element_order.index(element[0]) for element in elements]
    except ValueError:
        print(meeting_elements)
        raise
    if len(set(elements)) <= 3:
        return 0
    order_score = score_element_order(numbered_elements)
    return order_score


def score_element_order(element_list: List[any]) -> float:
    """Score the found meeting elements on how well they match the expected order."""
    element_set = sorted(list(set(element_list)))
    count = 0
    dummy_list = copy.copy(element_list)
    for i, e1 in enumerate(dummy_list):
        first = element_list.index(e1)
        rest = element_list[first+1:]
        for e2 in rest:
            if e2 > e1:
                count += 1
    set_size = len(element_set)
    order_max = set_size * (set_size - 1) / 2
    order_score = count / order_max
    return order_score


def find_meeting_line(line_id: str, meeting_lines: List[dict]) -> dict:
    """Find a specific line by id in the list of lines belonging to a meeting."""
    for line in meeting_lines:
        if line['metadata']['id'] == line_id:
            return line
    raise IndexError(f'Line with id {line_id} not in meeting lines.')


def generate_meeting_doc(meeting_metadata: dict, meeting_lines: list,
                         meeting_searcher: MeetingSearcher, column_metadata: Dict[str, dict]) -> iter:
    meeting = Meeting(meeting_searcher.current_date, meeting_metadata, column_metadata, lines=meeting_lines)
    # add number of lines to session info in meeting searcher
    session_info = meeting_searcher.sessions[meeting_metadata['meeting_date']][-1]
    session_info['num_lines'] = len(meeting_lines)
    if meeting.date.is_rest_day() or not meeting_searcher.has_meeting_date_match():
        return meeting
    # Check if the next meeting date is more than 1 workday ahead
    date_match = meeting_searcher.get_meeting_date_match()
    new_date = derive_date_from_string(date_match['match_keyword'], meeting_searcher.year)
    if meeting.date.isoformat() == new_date.isoformat():
        # print('SAME DAY:', meeting_searcher.current_date.isoformat(), '\t', meeting.date.isoformat())
        return meeting
    workday_shift = calculate_work_day_shift(new_date, meeting.date)
    # print('workday_shift:', workday_shift)
    if workday_shift > 1:
        print('MEETING DOC IS MULTI DAY')
        meeting.metadata['date_shift_status'] = 'multi_day'
    return meeting


def get_meeting_scans_version(meeting: Meeting) -> List:
    scans_version = {}
    for line in meeting.lines:
        scans_version[line['metadata']['doc_id']] = copy.copy(line['metadata']['scan_version'])
        scans_version[line['metadata']['doc_id']]['doc_id'] = line['metadata']['doc_id']
    # print("meeting scans versions:", scans_version)
    return list(scans_version.values())


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


def get_columns_metadata(sorted_pages: List[dict]) -> Dict[str, dict]:
    column_metadata = {}
    for page in sorted_pages:
        for column in page['columns']:
            column_id = column['metadata']['id']
            column_metadata[column_id] = column['metadata']
    return column_metadata


def get_meeting_dates(sorted_pages: List[dict], inv_config: dict,
                      inv_metadata: dict) -> Iterator[Meeting]:
    # TO DO: IMPROVEMENTS
    # - add holidays: Easter, Christmas
    # - make model year-dependent
    # - check for large date jumps and short meeting docs
    column_metadata = get_columns_metadata(sorted_pages)
    current_date = initialize_inventory_date(inv_metadata)
    meeting_searcher = MeetingSearcher(inv_config['inventory_num'], current_date,
                                       meeting_phrase_model, window_size=30)
    meeting_metadata = meeting_searcher.parse_meeting_metadata(None)
    gated_window = GatedWindow(window_size=10, open_threshold=400, shut_threshold=400)
    lines_skipped = 0
    print('indexing start for current date:', current_date.isoformat())
    meeting_lines = []
    word_freq_counter = read_word_freq_counter(inv_config, 'line')
    for li, line_info in enumerate(stream_resolution_page_lines(sorted_pages,
                                                                word_freq_counter=word_freq_counter)):
        # list all lines belonging to the same meeting date
        meeting_lines += [line_info]
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
            meeting_searcher.add_empty_document()
            # print(li, None)
        else:
            # add the line as a new document to the meeting searcher and search for meeting elements
            meeting_searcher.add_document(check_line['metadata']['id'], check_line['text'])
            # print(li, check_line['text'])
        # Keep sliding until the first line in the sliding window has matches
        # last_line = meeting_searcher.sliding_window[-1]
        # if not last_line:
        #     print(None)
        # else:
        #     print(li - 40, last_line['text_string'], [match['match_string'] for match in last_line['matches']])
        if not meeting_searcher.sliding_window[0] or len(meeting_searcher.sliding_window[0]['matches']) == 0:
            continue
        # get the meeting elements found in the lines of the sliding window
        meeting_elements = meeting_searcher.get_meeting_elements()
        # print(meeting_elements)
        # check if first meeting element is in the first line of the sliding window
        if len(meeting_elements.items()) == 0 or min(meeting_elements.values()) != 0:
            # move to next line if first meeting element is not in the first line of the sliding window
            continue
        if 'extract' in meeting_elements: # and meeting_elements['extract'] == 0:
            # what follows in the sliding window is an extract from earlier days, which looks
            # like a meeting opening but isn't. Reset the sliding window
            meeting_searcher.reset_sliding_window()
            continue
        if 'extract' in meeting_elements:
            for line in meeting_searcher.sliding_window:
                if not line:
                    continue
                print(line['metadata']['text_id'], line['text_string'])
        # score the found meeting elements for how well they match the order in which they are expected to appear
        # Empirically established threshold:
        # - need to match at least four meeting elements
        # - number of elements in expected order must be 80% of found elements
        # (so with four elements, all need to be in the right order, with five elements, one may be in wrong order)
        if score_meeting_elements(meeting_elements, num_elements_threshold=4) > 0.99:
            # for line in meeting_searcher.sliding_window:
            #     if not line:
            #         print(None)
            #     else:
            #         print(line['text_string'], [match['match_keyword'] for match in line['matches']])
            # get the first line of the new meeting day in the sliding window
            first_new_meeting_line_id = meeting_searcher.sliding_window[0]['text_id']
            # find that first line in the list of the collected meeting lines
            first_new_meeting_line = find_meeting_line(first_new_meeting_line_id, meeting_lines)
            # find the index of the first new meeting day line in the collected meeting lines
            new_meeting_index = meeting_lines.index(first_new_meeting_line)
            # everything before the first new meeting day line belongs to the previous day
            finished_meeting_lines = meeting_lines[:new_meeting_index]
            # everything after the first new meeting day line belongs to the new meeting day
            meeting_lines = meeting_lines[new_meeting_index:]
            meeting_doc = generate_meeting_doc(meeting_metadata, finished_meeting_lines,
                                               meeting_searcher, column_metadata)
            if meeting_doc.metadata['num_lines'] == 0:
                # A meeting with no lines only happens at the beginning
                # Don't generate a doc and sets the already shifted date back by 1 day
                # Also, reset the session counter
                meeting_searcher.sessions[meeting_doc.metadata['meeting_date']] = []
                date = meeting_searcher.current_date
                if date.month == 1 and 1 < date.day <= 4:
                    # reset_date = RepublicDate(date.year, 1, 1)
                    day_shift = date.day - 1
                    meeting_searcher.update_meeting_date(day_shift)
            else:
                yield meeting_doc
            # update the current meeting date in the searcher
            meeting_searcher.update_meeting_date()
            # update the searcher with new date strings for the next seven days
            meeting_searcher.update_meeting_date_searcher(num_dates=7)
            # get the meeting metadata for the new meeting date
            meeting_metadata = meeting_searcher.parse_meeting_metadata(meeting_doc.metadata)
            # reset the sliding window to search the next meeting opening
            meeting_searcher.shift_sliding_window()
    meeting_metadata['num_lines'] = len(meeting_lines)
    # after processing all lines in the inventory, create a meeting doc from the remaining lines
    yield generate_meeting_doc(meeting_metadata, meeting_lines, meeting_searcher, column_metadata)
