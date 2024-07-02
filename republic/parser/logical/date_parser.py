import datetime
import re
from collections import Counter
from collections import defaultdict
from typing import Dict, List, Set, Tuple, Union

import pagexml.model.physical_document_model as pdm
from fuzzy_search import FuzzyPhraseSearcher
from fuzzy_search import PhraseMatch

from republic.helper.pagexml_helper import make_baseline_string as mbs
from republic.model.republic_date import DateNameMapper
from republic.model.republic_date import RepublicDate
from republic.model.republic_date_phrase_model import week_day_names
from republic.model.republic_date_phrase_model import month_day_names
from republic.model.republic_date_phrase_model import month_names
from republic.model.inventory_mapping import get_inventory_text_type
from republic.model.inventory_mapping import get_inventory_by_id
from republic.model.inventory_mapping import get_inventory_by_num


def get_date_trs(pages):
    date_trs = []
    for page in pages:
        trs = []
        for col in page.columns:
            for tr in col.text_regions:
                if tr not in trs:
                    trs.append(tr)
        for tr in page.extra:
            if tr not in trs:
                trs.append(tr)
        for tr in page.text_regions:
            if tr not in trs:
                trs.append(tr)
        date_trs.extend([tr for tr in trs if 'date' in tr.type])
    return date_trs


def extract_best_date_match(matches: List[PhraseMatch], current_date: RepublicDate,
                            jump_days: int, date_strings: Dict[str, RepublicDate]) -> Union[None, PhraseMatch]:
    if len(matches) == 0:
        return None
    expected_date = current_date + datetime.timedelta(days=jump_days)
    sorted_matches = sorted(matches, key=lambda m: m.levenshtein_similarity, reverse=True)
    best_sim = sorted_matches[0].levenshtein_similarity
    best_matches = []
    for match in sorted_matches:
        if match.levenshtein_similarity != best_sim:
            break
        best_matches.append(match)
    if len(best_matches) > 1:
        best_delta = datetime.timedelta(days=36500)
        best_date, best_match = None, None
        for match in best_matches:
            match_date = date_strings[match.variant.phrase_string]
            time_delta = match_date - expected_date
            if time_delta < datetime.timedelta(days=0):
                continue
            if time_delta < best_delta:
                best_delta = time_delta
                best_match = match
            # print('MULTIPLE BEST MATCHES:', match)
    else:
        best_match = sorted_matches[0]
    return best_match


def make_date_searcher(date_mapper: DateNameMapper, config: Dict[str, any]) -> Dict[str, FuzzyPhraseSearcher]:
    return {
        'month': make_month_name_searcher(date_mapper, config),
        'week_day': make_week_day_name_searcher(date_mapper, config)
    }


def make_month_name_searcher(date_mapper: DateNameMapper, config: Dict[str, any]) -> FuzzyPhraseSearcher:
    phrase_list = [{'phrase': month_name} for month_name in date_mapper.date_name_map['month_name']]
    month_name_searcher = FuzzyPhraseSearcher(phrase_list=phrase_list, config=config)
    return month_name_searcher


def make_week_day_name_searcher(date_mapper: DateNameMapper, config: Dict[str, any]) -> FuzzyPhraseSearcher:
    phrase_list = []
    for week_day_name in date_mapper.date_name_map['week_day_name']:
        phrase = {
            'phrase': week_day_name,
            'max_start_offset': 3
        }
        phrase_list.append(phrase)
    week_day_name_searcher = FuzzyPhraseSearcher(phrase_list=phrase_list,
                                                 config=config)
    return week_day_name_searcher


def get_date_lines(date_trs):
    return [line for tr in date_trs for line in tr.lines if line.text]


def line_is_year(line: pdm.PageXMLTextLine) -> bool:
    if line.text is None or line.text == '':
        return False
    if m := re.search(r"(\b1[567]\d{2}\b)", line.text):
        year = m.group(1)
        return len(year) / len(line.text) > 0.5
    else:
        return False


def line_starts_with_week_day_name(line: pdm.PageXMLTextLine,
                                   week_day_name_searcher: FuzzyPhraseSearcher = None,
                                   ignorecase: bool = False, debug: int = 0):
    if line.text is None:
        return False
    # print('ignorecase:', ignorecase)
    line_text = line.text.lower() if ignorecase else line.text
    # print('line_text:', line_text)
    for set_version in week_day_names:
        if debug > 1:
            print('line_starts_with_week_day_name - set_version:', set_version)
            print('line_starts_with_week_day_name - week_day_names:', week_day_names[set_version])
            print('line_starts_with_week_day_name - line_text:', line_text)
        for week_day_name in week_day_names[set_version]:
            week_day_name = week_day_name.lower() if ignorecase else week_day_name
            # print('ignorecase:', ignorecase)
            if debug > 1:
                print(f'line_starts_with_week_day_name - line_text.startswith("{week_day_name}"):',
                      line_text.startswith(week_day_name))
            if line_text.startswith(week_day_name):
                return True
        if debug > 1:
            print('\n')
    if week_day_name_searcher is not None:
        matches = week_day_name_searcher.find_matches(line.text)
        if debug > 1:
            print('line_starts_with_week_day_name - fuzzy matching with week day names')
            for match in matches:
                print('line_starts_with_week_day_name - week_day_name match:', match)
        if len(matches) > 0:
            return True
    return False


def line_has_day_month(line: pdm.PageXMLTextLine,
                       month_name_searcher: FuzzyPhraseSearcher = None,
                       ignorecase: bool = False, debug: int = 0):
    if line.text is None:
        return False
    line_text = line.text.lower() if ignorecase else line.text
    found_month_name = None
    if month_name_searcher is not None:
        matches = month_name_searcher.find_matches(line.text, skip_exact_matching=False)
        if debug > 1:
            print('line_has_day_month - fuzzy matching with month day names')
            for match in matches:
                print('line_has_day_month - month_day_name match:', match)
        if len(matches) > 0:
            best_match = sorted(matches, key=lambda m: m.levenshtein_similarity)[-1]
            found_month_name = best_match.phrase.phrase_string
    if found_month_name is None:
        for set_version in month_names:
            if debug > 1:
                print('line_has_day_month - set_version:', set_version)
                print('line_has_day_month - month_names:', month_names[set_version])
                print('line_has_day_month - line_text:', line_text)
            for month_name in month_names[set_version]:
                month_name = month_name.lower() if ignorecase else month_name
                pattern = r"\b" + month_name + r"\b"
                match = re.search(pattern, line_text, re.IGNORECASE) if ignorecase else re.search(pattern, line_text)
                if debug > 1:
                    print(f'line_has_day_month - matching month {month_name} with line:', line_text)
                if match:
                    if debug > 1:
                        print(f'\t month {month_name} matches with line:', line_text)
                    found_month_name = month_name
            if debug > 1:
                print('\n')
    if found_month_name is not None:
        month_prefix = line_text.split(found_month_name)[0]
        if debug > 1:
            print(f"line_has_day_month - month_prefix: {month_prefix}")
        return re.match(r"\b\d+\b", month_prefix) is not None
    else:
        return False


def get_session_date_lines_from_pages(pages,
                                      month_name_searcher: FuzzyPhraseSearcher = None,
                                      week_day_name_searcher: FuzzyPhraseSearcher = None,
                                      ignorecase: bool = False, debug: int = 0):
    date_trs = get_date_trs(pages)
    if debug > 0:
        print('get_session_date_lines_from_pages - num date_trs:', len(date_trs))
    if debug > 1:
        for date_tr in date_trs:
            print('\tdate_tr:', date_tr.id)
    date_lines = get_date_lines(date_trs)
    if debug > 0:
        print('get_session_date_lines_from_pages - num date_lines:', len(date_lines))
    if debug > 1:
        for date_line in date_lines:
            print(f'\tdate_line: {mbs(date_line)}\t{date_line.text}')
    return filter_session_date_lines(date_lines, month_name_searcher=month_name_searcher,
                                     week_day_name_searcher=week_day_name_searcher,
                                     ignorecase=ignorecase, debug=debug)


def filter_session_date_lines(date_lines: List[pdm.PageXMLTextLine],
                              month_name_searcher: FuzzyPhraseSearcher = None,
                              week_day_name_searcher: FuzzyPhraseSearcher = None,
                              week_day_required: bool = True,
                              ignorecase: bool = False, debug: int = 0):
    """Filter on lines that start with the name of a week day."""
    session_date_lines = []
    for line in date_lines:
        if week_day_required and line_starts_with_week_day_name(line, week_day_name_searcher=week_day_name_searcher,
                                                                ignorecase=ignorecase, debug=debug):
            session_date_lines.append(line)
        elif line_has_day_month(line, month_name_searcher=month_name_searcher, ignorecase=ignorecase):
            session_date_lines.append(line)
    if debug > 0:
        print('filter_session_date_lines - num session_date_lines:', len(session_date_lines))
    return session_date_lines


def is_date_text_region(text_region: pdm.PageXMLTextRegion,
                        month_name_searcher: FuzzyPhraseSearcher = None,
                        week_day_name_searcher: FuzzyPhraseSearcher = None,
                        weekday_required: bool = True,
                        ignorecase: bool = False,
                        debug: int = 0) -> bool:
    first_line = text_region.lines[0]
    if weekday_required and line_starts_with_week_day_name(first_line, week_day_name_searcher=week_day_name_searcher,
                                                           ignorecase=ignorecase, debug=debug):
        return True
    elif weekday_required is False and line_has_day_month(first_line,
                                                          month_name_searcher=month_name_searcher,
                                                          ignorecase=ignorecase):
        return True
    else:
        return False


def filter_session_date_trs(date_trs: List[pdm.PageXMLTextRegion],
                            month_name_searcher: FuzzyPhraseSearcher = None,
                            week_day_name_searcher: FuzzyPhraseSearcher = None,
                            weekday_required: bool = True,
                            ignorecase: bool = False, debug: int = 0):
    """Filter on trs that start with the name of a week day."""
    session_date_trs = []
    for date_tr in date_trs:
        if is_date_text_region(date_tr, month_name_searcher=month_name_searcher,
                               week_day_name_searcher=week_day_name_searcher,
                               weekday_required=weekday_required, ignorecase=ignorecase):
            session_date_trs.append(date_tr)
    if debug > 0:
        print('filter_session_date_trs - num session_date_trs:', len(session_date_trs))
    return session_date_trs


def get_session_date_line_token_length(session_date_lines):
    line_token_lengths = [len(line.text.split(' ')) for line in session_date_lines]
    return max(line_token_lengths, key=line_token_lengths.count)


def get_standard_date_line_pos_tokens(standard_lines, ignorecase: bool = False):
    pos_tokens = defaultdict(list)
    for line in standard_lines:
        line_text = line.text.replace('. ', ' ').replace(', ', ' ')
        line_text = re.sub(r'[.,]$', '', line_text)
        if ignorecase:
            line_text = line_text.lower()
        tokens = line_text.split(' ')
        for pos, token in enumerate(tokens):
            pos_tokens[pos].append(token)
    return pos_tokens


def get_pos_cat_freq(pos_tokens: Dict[int, List[str]], date_token_cat: Dict[str, any],
                     text_type: str) -> Tuple[Dict[int, Counter], Dict[int, Counter]]:
    pos_cat_freq = defaultdict(Counter)
    pos_other_freq = defaultdict(Counter)
    for pos in pos_tokens:
        for token in pos_tokens[pos]:
            if token in date_token_cat or token.lower() in date_token_cat:
                match_token = token if token in date_token_cat else token.lower()
                for name_set, set_version in date_token_cat[match_token]:
                    if name_set in {'month_name', 'week_day_name'}:
                        if set_version != text_type:
                            continue
                    # print(pos, token, name_set, set_version)
                    pos_cat_freq[pos].update([(name_set, set_version)])
            elif token == 'den':
                pos_cat_freq[pos].update([('den', 'all')])
            elif re.match(r'^[xvij]+[ae]?n?$', token):
                pos_cat_freq[pos].update([('month_day_name', 'roman_early')])
            elif re.match(r'^\d+[ae]?n?$', token):
                pos_cat_freq[pos].update([('month_day_name', 'decimal_en')])
            else:
                pos_other_freq[pos].update([token])
    return pos_cat_freq, pos_other_freq


def get_session_date_line_structure(session_date_lines: List[pdm.PageXMLTextLine],
                                    date_token_cat: Dict[str, Set[Tuple[str, str]]],
                                    inventory_id: str, ignorecase: bool = False):
    """Returns a list of tuple specifing the format for each element of a date line.

    Example:
    [
        ('week_day_name', 'roman_early'),
        ('den', 'all'),
        ('month_day_name', 'decimal_en'),
        ('month_name', 'handwritten'),
    ]
    """
    try:
        line_token_length = get_session_date_line_token_length(session_date_lines)
    except ValueError:
        print(f'Error getting date_line_structure for inventory {inventory_id}')
        print(f'number of session_date_lines:', len(session_date_lines))
        raise
    text_type = get_inventory_text_type(inventory_id)
    standard_lines = [line for line in session_date_lines if len(line.text.split(' ')) == line_token_length]
    pos_tokens = get_standard_date_line_pos_tokens(standard_lines, ignorecase=ignorecase)
    pos_cat_freq, pos_other_freq = get_pos_cat_freq(pos_tokens, date_token_cat, text_type)
    date_elements = [pos_cat_freq[pos].most_common(1)[0][0] for pos in pos_cat_freq]
    return date_elements


def get_date_token_cat(inv_num: int = None, inv_id: str = None, ignorecase: bool = False):
    if inv_num:
        inv_metadata = get_inventory_by_num(inv_num)
        if inv_metadata is None:
            raise ValueError(f'invalid inv_num {inv_num}')
    elif inv_id:
        inv_metadata = get_inventory_by_id(inv_id)
        if inv_metadata is None:
            raise ValueError(f'invalid inv_id {inv_id}')
    else:
        raise ValueError('need to pass either inv_num or inv_id')
    date_token_map = {
        'month_name': month_names,
        'month_day_name': month_day_names,
        'week_day_name': week_day_names,
        'year': [str(year) for year in range(inv_metadata['year_start'], inv_metadata['year_end']+1)]
    }

    date_token_cat = defaultdict(set)

    for name_set in date_token_map:
        if name_set == 'year':
            for year_token in date_token_map[name_set]:
                if 3760 <= inv_metadata['inventory_num'] <= 3805:
                    set_version = 'printed_early'
                elif 3806 <= inv_metadata['inventory_num'] <= 3864:
                    set_version = 'printed_late'
                else:
                    set_version = 'handwritten'
                date_token_cat[year_token].add((name_set, set_version))
        else:
            for set_version in date_token_map[name_set]:
                for date_token in date_token_map[name_set][set_version]:
                    if ignorecase:
                        date_token = date_token.lower()
                    date_token_cat[date_token].add((name_set, set_version))

    return date_token_cat


def text_region_is_date(text_region: pdm.PageXMLTextRegion,
                        date_line_fraction_threshold: float = 0.65) -> bool:
    if text_region.stats['lines'] == 0:
        return False
    if text_region.has_type('date'):
        return True
    date_lines = []
    for line in text_region.lines:
        if 'line_class' in line.metadata and line.metadata['line_class'] == 'date':
            date_lines.append(line)
        elif line_is_year(line):
            date_lines.append(date_lines)
    return len(date_lines) / len(text_region.lines) > date_line_fraction_threshold


def identify_session_dates_in_page(page: pdm.PageXMLPage, date_line_fraction_threshold: float = 0.65):
    date_trs = []
    for col in page.columns:
        if col.stats['lines'] == 0:
            return None
        for tr in col.text_regions:
            if text_region_is_date(tr, date_line_fraction_threshold=date_line_fraction_threshold):
                date_trs.append(tr)
    return date_trs



