import re
from itertools import pairwise
from typing import Dict, List, Union

import pagexml.model.physical_document_model as pdm
import pandas as pd

from fuzzy_search import FuzzyPhraseSearcher

from republic.model.republic_date_phrase_model import month_abbrev_map


def get_page_content_type(page: pdm.PageXMLPage) -> str:
    default_types = ['structure_doc', 'physical_structure_doc', 'text_region', 'pagexml_doc', 'page']
    content_types = ['resolution_page', 'index_page', 'respect_page', 'unknown']
    for content_type in content_types:
        if page.has_type(content_type):
            return content_type
    raise TypeError(f"page {page.id} has no valid content type: {[pt for pt in page.type if pt not in default_types]}")


def get_tr_content_type(text_region: pdm.PageXMLTextRegion) -> List[str]:
    default_types = ['structure_doc', 'physical_structure_doc', 'text_region', 'pagexml_doc', 'page']
    return [trt for trt in text_region.type if trt not in default_types]


def get_header_dates(pages: List[pdm.PageXMLPage]) -> List[pdm.PageXMLTextRegion]:
    return [tr for page in pages for col in page.columns for tr in col.text_regions if tr.has_type('date')]


class DateRegionClassifier:

    def __init__(self, weekday_map: Dict[str, int], month_name_map: Dict[str, int]):
        self.weekday_map = weekday_map
        self.month_name_map = month_name_map
        self.search_config = {
            'levenshtein_threshold': 0.75
        }
        month_name_model = [{'phrase': month_name} for month_name in month_name_map]
        weekday_model = [{'phrase': weekday} for weekday in weekday_map]
        self.month_searcher = FuzzyPhraseSearcher(phrase_model=month_name_model,
                                                  config=self.search_config)
        self.weekday_searcher = FuzzyPhraseSearcher(phrase_model=weekday_model,
                                                    config=self.search_config)

    @staticmethod
    def has_roman_numeral(text_string: str) -> bool:
        """Check if a string has a Roman numeral (somewhat fuzzy), oriented towards
        session dates (accepting numerals to end in 'e' or 'en'. """
        if pd.isna(text_string) or text_string is None:
            return False
        return re.search(r'\b[xvi]+j?e?n?\b', text_string) is not None

    @staticmethod
    def has_year(text_string: str) -> bool:
        """Check if a string has a year within the period of the States General
        i.e. 1576-1796."""
        if pd.isna(text_string) or text_string is None:
            return False
        return re.search(r'\b1[567][0-9]{2}\b', text_string) is not None

    @staticmethod
    def get_year(text_string: str) -> Union[int, None]:
        """Extract the year from a string, if it contains any as a number"""
        if pd.isna(text_string) or text_string is None:
            return None
        if m := re.search(r'\b(15[789][0-9])\b', text_string):
            return int(m.group(1))
        else:
            return None

    def has_weekday(self, text_string: str) -> bool:
        return self.get_weekday(text_string) is not None

    def get_weekday(self, text_string: str):
        if pd.isna(text_string) or text_string is None:
            return None
        for weekday in self.weekday_map:
            if m := re.search(r"\b(" + weekday + r")\b", text_string, re.IGNORECASE):
                return m.group(1)
        matches = self.weekday_searcher.find_matches(text_string)
        if len(matches) == 0:
            return None
        if len(matches) == 1:
            return matches[0].phrase.phrase_string
        best_match = sorted(matches, key=lambda match: match.levenshtein_similarity)[0]
        return best_match.phrase.phrase_string

    def has_month(self, text_string: str):
        return self.get_month(text_string) is None

    def get_month(self, text_string: str, map_month: bool = False):
        if pd.isna(text_string) or text_string is None:
            return None
        for month_name in self.month_name_map:
            try:
                if m := re.search(r"\b(" + month_name + r")\b", text_string, re.IGNORECASE):
                    return month_name if map_month else m.group(1)
            except TypeError:
                print(f"Error checking for month {month_name} in text #{text_string}#")
                raise
        if m := re.match(r"\d+\.? ?([A-Z][a-z]{2,3})\b", text_string):
            abbrev_string = m.group(1)
            if abbrev_string in month_abbrev_map:
                return month_abbrev_map[abbrev_string]
        matches = self.month_searcher.find_matches(text_string)
        if len(matches) == 0:
            return None
        if len(matches) == 1:
            return matches[0].phrase.phrase_string
        best_match = sorted(matches, key=lambda match: match.levenshtein_similarity)[0]
        return best_match.phrase.phrase_string if map_month else best_match.string

    def get_month_num(self, text_string: str):
        if pd.isna(text_string) or text_string is None:
            return None
        for month_name in self.month_name_map:
            if month_name.lower() in text_string.lower():
                return self.month_name_map[month_name]
        return None

    def has_month_and_day(self, text_string: str):
        if pd.isna(text_string) or text_string is None:
            return False
        if self.has_month(text_string):
            month = self.get_month(text_string)
            assert month is not None, f"string has month {month} but cannot extract month"
            if re.search(r"\b([123]?[0-9])\b\W+" + f"{month}", text_string):
                return True
            if re.search(f"{month}" r"\W+\b([123]?[0-9])\b", text_string):
                return True

    def has_month_day(self, text_string: str) -> bool:
        if pd.isna(text_string) or text_string is None:
            return False
        if self.get_month_day(text_string):
            return True

    def get_month_and_day(self, text_string: str) -> Union[int, None]:
        if pd.isna(text_string) or text_string is None:
            return None
        month = self.get_month(text_string, map_month=False)
        if m := re.search(r"\b([123]?[0-9])\b\W+" + f"{month}", text_string):
            return int(m.group(1))
        if m := re.search(f"{month}" + r"\W+\b([123]?[0-9])\b", text_string):
            return int(m.group(1))
        return None

    @staticmethod
    def get_month_day(text_string: str):
        if pd.isna(text_string) or text_string is None:
            return None
        if m := re.search(r"\b([123]?[0-9])(e|en)?\b", text_string):
            return int(m.group(1))
        return None

    @staticmethod
    def is_second_session(text_string: str):
        if pd.isna(text_string) or text_string is None:
            return False
        if re.search(r"\b\wodem", text_string, re.IGNORECASE):
            return True
        if re.search(r"\bprand", text_string, re.IGNORECASE):
            return True
        if re.search(r"\wpres\b", text_string, re.IGNORECASE):
            return True
        return False

    @staticmethod
    def session_lang(text_string: str):
        if pd.isna(text_string) or text_string is None:
            return None
        if re.search(r"\bprand", text_string, re.IGNORECASE):
            return 'lt'
        if re.search(r"\wpres\b", text_string, re.IGNORECASE):
            return 'fr'
        if text_string.startswith('Le '):
            return 'fr'
        return None

    @staticmethod
    def classify_header_type(pandas_row: Dict[str, any]):
        if pandas_row['date_type'] == 'start':
            return None
        if isinstance(pandas_row['text'], float):
            return 'unknown'
        if 'secree' in pandas_row['text'].lower():
            return 'resolution_type'
        if 'besogne' in pandas_row['text'].lower():
            return 'resolution_type'
        if 'besoigne' in pandas_row['text'].lower():
            return 'resolution_type'
        else:
            return 'date'

    def classify_date_text(self, pandas_row: Dict[str, any], debug: int = 0):
        if pd.isna(pandas_row['text']):
            return 'unknown'
        if self.has_weekday(pandas_row['text']):
            if debug > 0:
                print('start - has_weekday:', pandas_row['text'])
            return 'start'
        if self.has_roman_numeral(pandas_row['text']):
            if debug > 0:
                print('start - has_weekday:', pandas_row['text'])
            return 'start'
        if re.search(r'\wrandi', pandas_row['text']):
            if debug > 0:
                print('start - has prandi:', pandas_row['text'])
            return 'start'
        if re.search(r'\wpres', pandas_row['text']):
            if debug > 0:
                print('start - has apres:', pandas_row['text'])
            return 'start'
        if re.search(r"\b15[789][0-9]*\b", pandas_row['text']):
            if debug > 0:
                print('start - has year:', pandas_row['text'])
            return 'start'
        if pandas_row['top'] > 400:
            if debug > 0:
                print('start - top > 400:', pandas_row['text'])
            return 'start'
        if pandas_row['page_num'] % 2 == 0:
            if debug > 0:
                print('header - left_indent < 500:', pandas_row['text'])
            return 'start'
        if pandas_row['num_lines'] > 1:
            if debug > 0:
                print('start - num_lines > 1:', pandas_row['text'])
            return 'start'
        if pandas_row['num_words'] > 3:
            if debug > 0:
                print('start - num_words > 3:', pandas_row['text'])
            return 'start'
        if pandas_row['left_indent'] > 1000:
            if debug > 0:
                print('start - left_indent > 1000:', pandas_row['text'])
            return 'start'
        if pandas_row['bottom'] < 400:
            if debug > 0:
                print('header - bottom < 400:', pandas_row['text'])
            return 'header'
        if pandas_row['left_indent'] < 500:
            if debug > 0:
                print('header - left_indent < 500:', pandas_row['text'])
            return 'header'
        else:
            if debug > 0:
                print('unknown - else reached:', pandas_row['text'])
            return 'unknown'


def read_date_text_regions_data(date_text_regions_file: str = None,
                                date_text_regions_frame: pd.DataFrame = None) -> Dict[str, List[any]]:
    df = None
    if date_text_regions_frame is not None:
        df = date_text_regions_frame
    elif date_text_regions_file is not None:
        df = pd.read_csv(date_text_regions_file, sep='\t')
    if df is None:
        raise ValueError(f"must pass either date_text_regions_file or date_text_regions_frame")
    """
    date_text_regions_data = {
        'inv_num': list(df.inv_num),
        'page_num': list(df.page_num),
        'id': list(df.id),
        'text': list(df.text),
        'month_num': list(df.month_num),
        'day_num': list(df.day_num),
        'date_type': list(df.date_type),
    }
    return date_text_regions_data
    """
    return df.to_dict('list')


class DateClassifier:

    def __init__(self, inv_id: str, period_start: str, period_end: str):
        self.inv_id = inv_id
        self.period_start = period_start
        self.period_end = period_end

    @staticmethod
    def is_na(i: Union[int, float]):
        if i is None:
            raise TypeError(f"item i must be int, float or NaN None")
        return pd.isna(i)

    @staticmethod
    def is_num(i: Union[int, float]):
        if i is None:
            raise TypeError(f"item i must be int, float or NaN None")
        return pd.isna(i) is False

    @staticmethod
    def is_same(i1, i2, is_num: bool = True):
        if is_num is True and (pd.isna(i1) or pd.isna(i2)):
            return False
        if is_num is False and (pd.isna(i1) and pd.isna(i2)):
            return True
        return i1 == i2

    @staticmethod
    def is_increment(i1, i2):
        if pd.isna(i1) or pd.isna(i2):
            return False
        return i1 + 1 == i2

    @staticmethod
    def is_not_end(month_num, month_day):
        if month_num == 2 and month_day < 24:
            return True
        return False

    @staticmethod
    def filter_seq(seq):
        return [i for i in seq if pd.isna(i) is False]

    @staticmethod
    def get_windows(drd, select_col: str, idx: int, window_size: int, filter_type: str = None):
        start = idx - window_size if idx > window_size else 0
        end = idx + 1 + window_size if idx + 1 + window_size < len(drd['month_num']) else len(drd['month_num'])
        if filter_type is None:
            prev_window = drd[select_col][start:idx]
            next_window = drd[select_col][idx + 1:end]
        else:
            prev_idxs = [i for i in range(start, idx) if drd['date_type'][i] == filter_type]
            # print(f"start: {start}, idx: {idx}, prev_idxs: {prev_idxs}")
            # print([drd['date_type'][i] for i in prev_idxs], [drd[select_col][i] for i in prev_idxs])
            prev_window = [drd[select_col][prev_idx] for prev_idx in prev_idxs]
            next_idxs = [i for i in range(idx+1, end) if drd['date_type'][i] == filter_type]
            # print(f"start: {start}, idx: {idx}, next_idxs: {next_idxs}")
            # print([drd['date_type'][i] for i in next_idxs], [drd[select_col][i] for i in next_idxs])
            next_window = [drd[select_col][next_idx] for next_idx in next_idxs]
        return prev_window, next_window

    @staticmethod
    def is_flat(seq):
        return len(set([i for i in seq if pd.isna(i) is False])) == 1

    @staticmethod
    def is_rising(seq):
        num_seq = [i for i in seq if pd.isna(i) is False]
        if len(set(num_seq)):
            return False
        for i1, i2 in pairwise(seq):
            if i1 > i2:
                return False
        return True


class ContextWindow:

    def __init__(self, curr_month, curr_day, curr_inv, curr_type,
                 prev_month, prev_day, prev_inv, prev_type,
                 next_month, next_day, next_inv, next_type):
        self.curr_month = curr_month
        self.curr_day = curr_day
        self.curr_inv = curr_inv
        self.curr_type = curr_type
        self.prev_month = prev_month
        self.prev_day = prev_day
        self.prev_inv = prev_inv
        self.prev_type = prev_type
        self.next_month = next_month
        self.next_day = next_day
        self.next_inv = next_inv
        self.next_type = next_type


def get_date_region_index(date_region_data: Dict[str, List[any]], i: int):
    return (date_region_data['month_num'][i],
            date_region_data['day_num'][i],
            date_region_data['inv_num'][i],
            date_region_data['date_type'][i])


def get_context_window(date_region_data: Dict[str, List[any]], i: int):
    curr_month, curr_day, curr_inv, curr_type = get_date_region_index(date_region_data, i)
    if i - 1 >= 0:
        prev_month, prev_day, prev_inv, prev_type = get_date_region_index(date_region_data, i-1)
    else:
        prev_month, prev_day, prev_inv, prev_type = None, None, None, None
    if i + 1 < len(date_region_data['month_num']):
        next_month, next_day, next_inv, next_type = get_date_region_index(date_region_data, i+1)
    else:
        next_month, next_day, next_inv, next_type = None, None, None, None
    return ContextWindow(curr_month, curr_day, curr_inv, curr_type,
                         prev_month, prev_day, prev_inv, prev_type,
                         next_month, next_day, next_inv, next_type)


def categorise_header_type(row):
    most_found = max([row['month'], row['day_num']])
    if row['header_placement'] == 'rarely':
        return 'no_headers'
    if most_found / row['num_headers'] > 0.4:
        return 'date'
    elif most_found / row['num_headers'] < 0.2:
        return 'no_date'
    else:
        return 'unknown'


def categorise_date_header_placement(row):
    if row['num_headers'] / row['num_recto'] > 0.8:
        return 'mostly'
    if row['num_headers'] / row['num_recto'] > 0.2:
        return 'regularly'
    else:
        return 'rarely'


def categorise_header_date_ratio(header_date_ratio):
    if header_date_ratio > 0.9:
        return 'complete_date_headers'
    elif header_date_ratio > 0.2:
        return 'incomplete_date_headers'
    else:
        return 'no_date_headers'


def get_header_date_counts(df):
    date_cols = ['month', 'month_num', 'year', 'day_num']

    temp = df[['inv_num', 'num_scans', 'num_recto_pages']].to_dict()
    num_recto = {temp['inv_num'][idx]: temp['num_recto_pages'][idx] for idx in temp['inv_num']}
    num_scans = {temp['inv_num'][idx]: temp['num_scans'][idx] for idx in temp['inv_num']}

    headers = df[(df.date_type == 'header')]
    header_counts = headers.inv_num.value_counts()

    header_date_counts = headers.groupby('inv_num')[date_cols].count()
    header_date_counts = header_date_counts.reset_index()

    header_date_counts['num_headers'] = header_date_counts.inv_num.apply(lambda x: header_counts[x])
    header_date_counts['num_scans'] = header_date_counts.inv_num.apply(lambda x: num_scans[x])
    header_date_counts['num_recto'] = header_date_counts.inv_num.apply(lambda x: num_recto[x])
    header_date_counts = header_date_counts.set_index('inv_num')

    header_date_counts['header_ratio'] = header_date_counts.apply(lambda row: row['num_headers'] / row['num_recto'],
                                                                  axis=1)
    header_date_counts['header_date_ratio'] = header_date_counts.apply(lambda row: row['month'] / row['num_headers'],
                                                                       axis=1)
    header_date_counts['header_date_cat'] = header_date_counts.header_date_ratio.apply(categorise_header_date_ratio)
    header_date_counts['header_placement'] = header_date_counts.apply(categorise_date_header_placement, axis=1)
    header_date_counts['header_type'] = header_date_counts.apply(categorise_header_type, axis=1)
    return header_date_counts
