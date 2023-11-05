import re
from collections import Counter
from collections import defaultdict
from typing import Dict, List, Set, Tuple

import pagexml.model.physical_document_model as pdm

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


def get_date_lines(date_trs):
    return [line for tr in date_trs for line in tr.lines if line.text]


def check_line_starts_with_week_day_name(line: pdm.PageXMLTextLine, ignorecase: bool = False, debug: int = 0):
    if line.text is None:
        return False
    # print('ignorecase:', ignorecase)
    line_text = line.text.lower() if ignorecase else line.text
    # print('line_text:', line_text)
    for set_version in week_day_names:
        if debug > 1:
            print('check_line_starts_with_week_day_name - set_version:', set_version)
            print('check_line_starts_with_week_day_name - week_day_names:', week_day_names[set_version])
            print('check_line_starts_with_week_day_name - line_text:', line_text)
        for week_day_name in week_day_names[set_version]:
            week_day_name = week_day_name.lower() if ignorecase else week_day_name
            # print('ignorecase:', ignorecase)
            if debug > 1:
                print(f'check_line_starts_with_week_day_name - line_text.startswith("{week_day_name}"):',
                      line_text.startswith(week_day_name))
            if line_text.startswith(week_day_name):
                return True
        if debug > 1:
            print('\n')
    return False


def get_session_date_lines_from_pages(pages, ignorecase: bool = False, debug: int = 0):
    date_trs = get_date_trs(pages)
    if debug > 0:
        print('get_session_date_lines_from_pages - num date_trs:', len(date_trs))
    date_lines = get_date_lines(date_trs)
    if debug > 0:
        print('get_session_date_lines_from_pages - num date_lines:', len(date_lines))
    return filter_session_date_lines(date_lines, ignorecase=ignorecase, debug=debug)


def filter_session_date_lines(date_lines, ignorecase: bool = False, debug: int = 0):
    session_date_lines = []
    for line in date_lines:
        if check_line_starts_with_week_day_name(line, ignorecase=ignorecase, debug=debug):
            session_date_lines.append(line)
    if debug > 0:
        print('filter_session_date_lines - num session_date_lines:', len(session_date_lines))
    return session_date_lines


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
    line_token_length = get_session_date_line_token_length(session_date_lines)
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
