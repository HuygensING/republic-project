from typing import List, Dict, Union
import copy
import datetime

from republic.model.inventory_mapping import get_inventory_by_num
from republic.model.republic_phrase_model import month_names_late, month_names_early
from republic.model.republic_phrase_model import week_day_name_map, week_day_names
from republic.fuzzy.fuzzy_keyword_searcher import FuzzyKeywordSearcher
from republic.parser.pagexml.pagexml_textregion_parser import get_textregion_text


strict_config = {
    "char_match_threshold": 0.6,
    "ngram_threshold": 0.5,
    "levenshtein_threshold": 0.6,
    "max_length_variance": 3,
    "use_word_boundaries": False,
    "perform_strip_suffix": False,
    "ignorecase": False,
    "ngram_size": 2,
    "skip_size": 2,
}
attendance_config = {
    "char_match_threshold": 0.6,
    "ngram_threshold": 0.5,
    "levenshtein_threshold": 0.6,
    "max_length_variance": 3,
    "use_word_boundaries": False,
    "perform_strip_suffix": False,
    "ignorecase": False,
    "ngram_size": 2,
    "skip_size": 2,
}
attendance_keywords = [
    'PRAESIDE,',
    'Den Heere',
    'PRAESENTIBUS,',
    'De Heeren',
    # 'Nihil aftum eft'
]
attendance_variants = {
    'PRAESIDE,': ['P R AE S I D E,'],
    'PRAESENTIBUS,': ['P R AE S E N T I B U S,']
}


def initialize_attendance_searcher(year: int, config: Union[dict, None] = None,
                                   keywords: Union[list, None] = None,
                                   variants: Union[dict, None] = None) -> FuzzyKeywordSearcher:
    """Initialize a FuzzyKeywordSearcher with phrases for attendence list formulas."""
    if not config:
        config = attendance_config
    if not keywords:
        keywords = attendance_keywords
    if not variants:
        variants = attendance_variants
    attendance_searcher = FuzzyKeywordSearcher(config)
    attendance_searcher.index_keywords(keywords + [str(year)])
    attendance_searcher.index_spelling_variants(variants)
    return attendance_searcher


def get_next_month(current_date: dict) -> int:
    assert(1 <= current_date['month'] <= 12)
    next_month = current_date['month'] + 1
    if next_month > 12:
        next_month = 1
    assert(1 <= next_month <= 12)
    return next_month


def get_next_weekday(current_date: dict) -> str:
    next_index = week_day_names.index(current_date['weekday']) + 1
    if next_index >= len(week_day_names):
        next_index = 0
    return week_day_names[next_index]


def get_next_month_day(current_date: dict) -> tuple:
    next_day_num = current_date['day_num'] + 1
    # assume next date has same month
    next_month = current_date['month']
    turnover_month = False
    if next_month == 2:
        if next_day_num > 28 and current_date['year'] % 4 != 0 or next_day_num > 29 and current_date['year'] % 4 == 0:
            turnover_month = True
    elif next_month in [1, 3, 5, 7, 8, 10, 12]:
        if next_day_num > 31:
            turnover_month = True
    else:
        if next_day_num > 30:
            turnover_month = True
    if turnover_month:
        next_day_num = 1
        next_month = get_next_month(current_date)
    return next_month, next_day_num


def get_next_date(current_date: dict) -> dict:
    next_month, next_day_num = get_next_month_day(current_date)
    next_year = current_date['year']
    if next_month == 1 and current_date['month'] == 12:
        next_year = current_date['year'] + 1
    return {
        'weekday': get_next_weekday(current_date),
        'day_num': next_day_num,
        'month': next_month,
        'year': next_year
    }


def get_date_text_string(current_date: dict, include_year: bool = True) -> str:
    month_name = get_current_date_month(current_date)
    if include_year:
        return f'{current_date["weekday"]} den {current_date["day_num"]} {month_name} {current_date["year"]}.'
    else:
        return f'{current_date["weekday"]} den {current_date["day_num"]} {month_name}'


def get_next_date_strings(current_date: dict, num_dates: int = 3, include_year: bool = True) -> List[str]:
    date_strings = [get_date_text_string(current_date, include_year=include_year)]
    next_date = get_next_date(current_date)
    for i in range(1, num_dates):
        date_strings += [get_date_text_string(next_date, include_year=include_year)]
        next_date = get_next_date(next_date)
    return date_strings


def update_meeting_date_searcher(date_strings: List[str]) -> FuzzyKeywordSearcher:
    meeting_date_searcher = FuzzyKeywordSearcher(strict_config)
    meeting_date_searcher.index_keywords(date_strings)
    return meeting_date_searcher


def get_current_date_month(current_date):
    if current_date['year'] > 1750:
        month_names = month_names_late
    else:
        month_names = month_names_early
    return month_names[current_date['month'] - 1]


def is_date_dict(date: any) -> False:
    if not isinstance(date, dict):
        return False
    if 'year' in date and 'month' in date and 'day_num' in date:
        return True
    return False


def determine_week_day_name(current_date: Union[datetime.date, dict]) -> str:
    """
    This function returns the name of the week day given a date,
    using 1 January 1770 as reference date, which is a Monday.
    """
    if is_date_dict(current_date):
        current_date = make_date_object(current_date)
    reference_date = datetime.date(1770, 1, 1)
    reference_week_day_name = 'Lunae'
    date_diff = current_date - reference_date
    current_week_day_num = (week_day_name_map[reference_week_day_name] + date_diff.days) % 7
    current_week_day_name = week_day_names[current_week_day_num - 1]
    return current_week_day_name


def initialize_inventory_date(inventory_num: int) -> Dict[str, Union[str, int]]:
    inventory_info = get_inventory_by_num(inventory_num)
    year = inventory_info['year']
    new_years_day = datetime.date(year, 1, 1)
    return {
        'year': year,
        'month': 1,
        'day_num': 1,
        'weekday': determine_week_day_name(new_years_day)
    }


def make_date_object(current_date: dict) -> datetime.date:
    date = datetime.date(current_date['year'], current_date['month'], current_date['day_num'])
    return date


def make_meeting_date_string(current_date):
    return datetime.date(current_date['year'], current_date['month'], current_date['day_num']).isoformat()


def make_paragraph(page: dict, textregion: dict, current_date: Dict[str, Union[str, int]],
                   ci: int, ti: int, meetingdate_start: bool) -> dict:
    paragraph_id = page['metadata']['page_id'] + f'col-{ci}-tr-{ti}'
    meetingdate = make_meeting_date_string(current_date)
    text = get_textregion_text(textregion)
    return {
        'id': paragraph_id,
        'text': text,
        'meetingdate': meetingdate,
        'meetingdate_year': current_date['year'],
        'meetingdate_month': current_date['month'],
        'meetingdate_day': current_date['day_num'],
        'meetingdate_weekday': current_date['weekday'],
        'meetingdate_string': get_date_text_string(current_date),
        'meetingdate_start': meetingdate_start,
        'inventory_num': page['metadata']['inventory_num'],
        'scan_id': page['metadata']['scan_id'],
        'page_id': page['metadata']['page_id'],
        'column_num': ci+1,
        'textregion': ti+1,
        'coords': textregion['coords']
    }


def update_meeting_date(current_date: Dict[str, Union[str, int]], date_strings: List[str],
                        meeting_matches: List[dict]) -> tuple:
    last_index = 0
    for match in meeting_matches:
        index = date_strings.index(match['match_keyword'])
        if index > last_index:
            last_index = index
    for i in range(0, last_index):
        current_date = get_next_date(current_date)
        # print('\tupdating current date:', current_date)
    next_date = get_next_date(current_date)
    return current_date, next_date


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


def stream_resolution_page_lines(pages: list) -> Union[None, iter]:
    for page in sorted(pages, key=lambda x: x['metadata']['page_num']):
        for ci, column in enumerate(page['columns']):
            for ti, textregion in enumerate(column['textregions']):
                if 'lines' not in textregion or not textregion['lines']:
                    continue
                for li, line in enumerate(textregion['lines']):
                    yield {
                        'id': page['metadata']['page_id'] + f'-col-{ci}-tr-{ti}-line-{li}',
                        'page_id': page['metadata']['page_id'],
                        'page_num': page['metadata']['page_num'],
                        'column_index': ci,
                        'textregion_index': ti,
                        'textregion_id': page['metadata']['page_id'] + f'-col-{ci}-tr-{ti}',
                        'line_index': li,
                        'coords': line['coords'],
                        'text': line['text']
                    }
    return None


def print_line_info(line_info: dict) -> None:
    print('\t', line_info['page_num'], line_info['column_index'],
          line_info['textregion_index'], line_info['line_index'],
          line_info['coords']['top'], line_info['coords']['bottom'],
          line_info['coords']['left'], line_info['coords']['right'],
          line_info['text'])


def get_meeting_elements(sliding_window: List[dict], year: int) -> Dict[str, int]:
    meeting_elements = {}
    for li, line_info in enumerate(sliding_window):
        if line_info['meeting_matches']:
            meeting_elements['meeting_date'] = li
        for match in line_info['attendance_matches']:
            if match['match_keyword'] == str(year):
                meeting_elements['meeting_year'] = li
            if match['match_keyword'] in attendance_keywords:
                meeting_elements[match['match_keyword']] = li
    return meeting_elements


def score_meeting_elements(meeting_elements: Dict[str, int]) -> float:
    elements = sorted(meeting_elements.items(), key=lambda x: x[1])
    order = ['meeting_date', 'meeting_year', 'PRAESIDE,', 'Den Heere', 'PRAESENTIBUS,', 'De Heeren']
    numbered_elements = [order.index(element[0]) for element in elements]
    if len(set(elements)) <= 3:
        return 0
    order_score = score_element_order(numbered_elements)
    return order_score


def parse_meeting_metadata(meeting_elements: Dict[str, int], current_date: Dict[str, Union[str, int]],
                           sliding_window: List[dict]) -> dict:
    # print('\tFOUND MEETING START')
    # print('\t', meeting_elements)
    meeting_date = datetime.date(current_date['year'], current_date['month'], current_date['day_num']).isoformat()
    meeting_metadata = {
        'id': f'meeting-{meeting_date}',
        'meeting_date': current_date,
        'lines': [sliding_window],
        'has_meeting_date_element': False
    }
    for meeting_element, line_index in sorted(meeting_elements.items(), key=lambda x: x[1]):
        line_info = sliding_window[line_index]
        # print_line_info(line_info)
        if meeting_element == 'meeting_date':
            meeting_metadata['has_meeting_date_element'] = True
            meeting_metadata['meeting_date']['line_id'] = line_info['id']
            meeting_metadata['meeting_date']['text_matches'] = line_info['meeting_matches']
        if meeting_element == 'Den Heere':
            president_name = None
            for match in line_info['attendance_matches']:
                if match['match_keyword'] == 'Den Heere':
                    start_offset = line_info['text'].index(match['match_string'])
                    end_offset = start_offset + len(match['match_string'])
                    president_name = line_info['text'][end_offset:]
            meeting_metadata['president'] = {
                'line_id': line_info['id'],
                'president_name': president_name
            }
    return meeting_metadata


def score_element_order(element_list: List[any]) -> float:
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


def get_meeting_dates(sorted_pages: List[dict], inv_num: int) -> iter:
    current_date = initialize_inventory_date(inv_num)
    date_strings = get_next_date_strings(current_date, num_dates=7, include_year=False)
    attendance_searcher = initialize_attendance_searcher(current_date['year'])
    meetingdate_searcher = update_meeting_date_searcher(date_strings)
    sliding_window = []
    sliding_window_size = 20
    meeting_metadata = None
    print('indexing start for current date:', current_date)
    print('date_strings:', date_strings)
    meeting_lines = []
    for li, line_info in enumerate(stream_resolution_page_lines(sorted_pages)):
        # list all lines belonging to the same meeting date
        meeting_lines += [line_info]
        if not line_info['text']:
            continue
        line_info['attendance_matches'] = attendance_searcher.find_candidates(line_info['text'],
                                                                              use_word_boundaries=False,
                                                                              include_variants=True)
        line_info['meeting_matches'] = meetingdate_searcher.find_candidates(line_info['text'],
                                                                            use_word_boundaries=False,
                                                                            include_variants=True)
        if len(sliding_window) < sliding_window_size:
            sliding_window += [line_info]
        else:
            sliding_window = sliding_window[1:] + [line_info]
        meeting_elements = get_meeting_elements(sliding_window, current_date['year'])
        meeting_score = score_meeting_elements(meeting_elements)
        if meeting_score > 0.8 and min(meeting_elements.values()) == 0:
            first_new_meeting_line = sliding_window[0]
            new_meeting_index = meeting_lines.index(first_new_meeting_line)
            if first_new_meeting_line in meeting_lines:
                print('\tfirst_new_meeting_line:', meeting_lines.index(first_new_meeting_line))
            meeting_date = datetime.date(current_date['year'],
                                         current_date['month'],
                                         current_date['day_num']).isoformat()
            yield {
                'id': f'meeting-{meeting_date}',
                "inventory_num": inv_num,
                "year": current_date["year"],
                "meeting_date": current_date,
                "meeting_metadata": meeting_metadata,
                "meeting_lines": meeting_lines[:new_meeting_index]
            }
            meeting_lines = meeting_lines[new_meeting_index:]
            has_meeting_date_element = False
            for meeting_element in meeting_elements:
                line_info = sliding_window[meeting_elements[meeting_element]]
                if meeting_element == 'meeting_date':
                    has_meeting_date_element = True
                    current_date, next_date = update_meeting_date(current_date,
                                                                  date_strings,
                                                                  line_info['meeting_matches'])
                    date_strings = get_next_date_strings(current_date, num_dates=7, include_year=False)
                    meetingdate_searcher = update_meeting_date_searcher(date_strings)
                    print('\tcurrent_date:', current_date)
            if not has_meeting_date_element:
                # Dirty hack: no explicit meeting date string found, assume this is the next day, but string
                # is missing or not recognised.
                current_date = get_next_date(current_date)
                date_strings = get_next_date_strings(current_date, num_dates=7, include_year=False)
                meetingdate_searcher = update_meeting_date_searcher(date_strings)
            meeting_metadata = parse_meeting_metadata(meeting_elements, current_date, sliding_window)
            sliding_window = []
    meeting_date = datetime.date(current_date['year'],
                                 current_date['month'],
                                 current_date['day_num']).isoformat()
    yield {
        'id': f'meeting-{meeting_date}',
        "inventory_num": inv_num,
        "year": current_date["year"],
        "meeting_date": current_date,
        "meeting_metadata": meeting_metadata,
        "meeting_lines": meeting_lines
    }


