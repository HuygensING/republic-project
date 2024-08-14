import copy
from typing import Callable, Dict, List, Union

import numpy as np
import pandas as pd

from republic.classification.content_classification import DateClassifier
from republic.classification.content_classification import read_date_text_regions_data
from republic.classification.content_classification import get_context_window


def rule_month_1(date_classifier, drd: Dict[str, List[any]], i: int, window_size: int = 3):
    """Impute month number if surrounding regions all have the same month.

    ### Situation 1: imputing missing months

    A date region $t_i$ has no known month. If the preceding $T_{i-x,i-1}$ date regions and
    the following date regions $T_{i+1,i+x}$ all have the same month $m$, then assign $m$
    to $t_i$."""
    if date_classifier.is_na(drd['month_num'][i]) is False:
        # month is known, so nothing to impute
        return drd['month_num'][i], drd['day_num'][i]
    if i == 0 or i == len(drd['month_num']) - 1:
        # can't compare before and after for first and last region
        return drd['month_num'][i], drd['day_num'][i]
    prev_months, next_months = date_classifier.get_windows(drd, 'month_num', i, window_size)
    prev_months = date_classifier.filter_seq(prev_months)
    next_months = date_classifier.filter_seq(next_months)
    if len(prev_months) > 1 and len(next_months) > 1 and date_classifier.is_flat(prev_months + next_months):
        return prev_months[0], drd['day_num'][i]
    else:
        return drd['month_num'][i], drd['day_num'][i]


def rule_month_2(date_classifier, drd: Dict[str, List[any]], i: int, window_size: int = 3):
    """Correct month number if surrounding regions all have the same month but current month differs."""
    cw = get_context_window(drd, i)
    if date_classifier.is_na(cw.curr_month):
        # month is unknown, so not a mistake, skip
        return cw.curr_month, cw.curr_day
    if i == 0 or i == len(drd['month_num']) - 1:
        # can't compare before and after for first and last region, skip
        return cw.curr_month, cw.curr_day
    prev_months, next_months = date_classifier.get_windows(drd, 'month_num', i, window_size, filter_type='header')
    prev_months = date_classifier.filter_seq(prev_months)
    next_months = date_classifier.filter_seq(next_months)
    if len(prev_months) == 0 or len(next_months) == 0:
        # no month info before or after, skip
        return cw.curr_month, cw.curr_day
    if date_classifier.is_flat(prev_months + next_months) and cw.curr_month != prev_months[0]:
        # print(i, '\t', prev_months, cw.curr_month, next_months, '\t', cw.prev_day, cw.curr_day, cw.next_day)
        return prev_months[0], cw.curr_day
    else:
        return cw.curr_month, cw.curr_day


def rule_month_3(date_classifier, drd: Dict[str, List[any]], i: int):
    """### Situation 3: month imputation within context of increasing day numbers

    Current date region $t_i$ has no known month.  If the previous date region $t_{i-1}$ has a month $m$
    and day $d_i$ and the next date region $t_{i+1}$ has the same month $m$ an day $d_j$ such that
    $j <= i$ (it is either the same day or a later day in the same month), than assume that the current
    date region also has month $m$."""
    cw = get_context_window(drd, i)
    if i == 0 or i == len(drd['month_num']) - 1:
        return cw.curr_month, cw.curr_day
    if date_classifier.is_num(cw.curr_month):
        return cw.curr_month, cw.curr_day
    # print(i, '\t', cw.prev_month, cw.curr_month, cw.next_month, '\t', cw.prev_day, cw.curr_day, cw.next_day)
    if date_classifier.is_na(cw.prev_month) or date_classifier.is_na(cw.next_month):
        return cw.curr_month, cw.curr_day
    if date_classifier.is_na(cw.prev_day) or date_classifier.is_na(cw.next_day):
        # print(cw.prev_month, cw.curr_month, cw.prev_day, cw.curr_day)
        return cw.curr_month, cw.curr_day
    if cw.prev_month == cw.next_month and cw.next_day >= cw.prev_day:  # -1 <= next_day - prev_day <= 0:
        # print(i, cw.prev_month, cw.curr_month, cw.prev_day, cw.curr_day)
        return cw.prev_month, cw.prev_day
    else:
        return cw.curr_month, cw.curr_day


def rule_day_4(date_classifier, drd: Dict[str, List[any]], i: int):
    """
    ### Rule 4: day number imputation within context of same day number

    The current date region $t_i$ has the same month $m(t)$ as the previous $t_{i-1}$ and next date region
    $t_{i+1}$. If $t_i$ has no day information but $t_{i-1}$ and $t_{i+1}$ have the same day
    ($d(t_{i-1})$ == $d(t_{i+1})$) then $d(t_i)$ is also the same.

    """
    cw = get_context_window(drd, i)
    if date_classifier.is_num(cw.curr_day):
        return cw.curr_month, cw.curr_day
    if date_classifier.is_na(cw.curr_month):
        return cw.curr_month, cw.curr_day
    if date_classifier.is_flat([cw.prev_month, cw.curr_month, cw.next_month]) and \
            date_classifier.is_same(cw.prev_day, cw.next_day, is_num=True):
        return cw.curr_month, cw.prev_day
    else:
        return cw.curr_month, cw.curr_day


def rule_day_5(date_classifier, drd: Dict[str, List[any]], i: int):
    """
    ### Situation 5: day number imputation

    - If the previous date region is a `header` and the next date region is a `header` and the current
        region is a session `start`:
    - If prev and next have the same month and the same day, than the `start` region is probably a
        second session on the same day.
    - If prev and next have the same month but next has a higher day, than `start` is probably the
        start of the session on the day of the next `header` region.
    """
    cw = get_context_window(drd, i)
    if cw.curr_type != 'start' or cw.prev_type != 'header' or cw.next_type != 'header':
        # not the header - start - header pattern, so skip
        return cw.curr_month, cw.curr_day
    if date_classifier.is_num(cw.curr_month) and date_classifier.is_num(cw.curr_day):
        # month and day already known, so skip
        return cw.curr_month, cw.curr_day
    if cw.prev_month != cw.next_month:
        # previous month is not the same as the next month, so skip
        return cw.curr_month, cw.curr_day
    if date_classifier.is_num(cw.curr_month) and (cw.curr_month != cw.prev_month):
        # print(i, '\t', cw.prev_month, cw.curr_month, cw.next_month, '\t', cw.prev_day, cw.curr_day, cw.next_day)
        # current month deviates from previous and next month, so is maybe not a proper date region, skip
        return cw.curr_month, cw.curr_day
    if date_classifier.is_na(cw.prev_day) or date_classifier.is_na(cw.next_day):
        # previous day or next day is unknown, so skip
        return cw.curr_month, cw.curr_day
    if date_classifier.is_same(cw.prev_day, cw.next_day, is_num=True):
        # previous day and next day are the same, so current month and day are the same as previous month and day
        return cw.prev_month, cw.prev_day
    if cw.prev_day + 1 == cw.next_day:
        # previous day is one day before next day, so current month and day are the same as next month and day
        return cw.prev_month, cw.next_day
    else:
        return cw.curr_month, cw.curr_day


def rule_month_6(date_classifier, drd: Dict[str, List[any]], i: int):
    cw = get_context_window(drd, i)
    if 'check' not in drd:
        drd['check'] = [np.nan for _ in range(len(drd['month_num']))]
    if cw.prev_month is None:
        # first date in the list, so previous doesn't exist, skip
        return cw.curr_month, cw.curr_day
    if date_classifier.is_na(cw.curr_month) or date_classifier.is_na(cw.prev_month):
        # either current or previous month is unknown, so skip
        return cw.curr_month, cw.curr_day
    if cw.prev_month > cw.curr_month:
        # previous month is higher than current month so something is wrong
        # print('PREV MONTH HIGHER THAN CURRENT MONTH')
        # print(i, '\t', cw.prev_month, cw.curr_month, cw.next_month, '\t', cw.prev_day, cw.curr_day, cw.next_day)
        reason = 'prev_month_higher_than_current'
        add_check(drd, i, reason)
        # add_check(check_idx, i, 'prev_month_higher_than_current')
        return cw.curr_month, cw.curr_day
    if cw.curr_month - cw.prev_month > 1.0:
        # previous month is higher than current month so something is wrong
        # print('BIG JUMP FROM PREV MONTH TO CURRENT MONTH')
        # print(i, '\t', cw.prev_month, cw.curr_month, cw.next_month, '\t', cw.prev_day, cw.curr_day, cw.next_day)
        reason = 'large_gap_prev_month_to_current'
        add_check(drd, i, reason)
        # add_check(check_idx, i, 'large_gap_prev_month_to_current')
        return cw.curr_month, cw.curr_day

    else:
        return cw.curr_month, cw.curr_day


def rule_day_7(date_classifier, drd: Dict[str, List[any]], i: int):
    cw = get_context_window(drd, i)
    if 'check' not in drd:
        drd['check'] = [np.nan for _ in range(len(drd['month_num']))]
    if cw.prev_month is None:
        # first date in the list, so previous doesn't exist, skip
        return cw.curr_month, cw.curr_day
    if date_classifier.is_na(cw.curr_month) or date_classifier.is_na(cw.prev_month):
        # either current or previous month is unknown, so skip
        return cw.curr_month, cw.curr_day
    if date_classifier.is_na(cw.curr_day) or date_classifier.is_na(cw.prev_day):
        # either current or previous day is unknown, so skip
        return cw.curr_month, cw.curr_day
    if cw.prev_month != cw.next_month:
        # current and previous month are not the same, so skip
        return cw.curr_month, cw.curr_day
    if date_classifier.is_num(cw.next_day) and cw.prev_day != cw.curr_day and cw.prev_day == cw.next_day:
        # check_idx.append(i)
        pass
    if cw.prev_day > cw.curr_day:
        # previous day is higher than current day so something is wrong
        # print('PREV DAY HIGHER THAN CURRENT DAY')
        # print(i, '\t', cw.prev_month, cw.curr_month, cw.next_month, '\t', cw.prev_day, cw.curr_day, cw.next_day)
        reason = 'prev_day_higher_than_current'
        add_check(drd, i, reason)
        return cw.curr_month, cw.curr_day
    if cw.curr_day - cw.prev_day > 1.0:
        # previous month is higher than current month so something is wrong
        # print('BIG JUMP FROM PREV DAY TO CURRENT DAY')
        # print(i, '\t', cw.prev_month, cw.curr_month, cw.next_month, '\t', cw.prev_day, cw.curr_day, cw.next_day)
        reason = 'large_gap_prev_day_to_current'
        add_check(drd, i, reason)
        return cw.curr_month, cw.curr_day

    else:
        return cw.curr_month, cw.curr_day


def check_start_in_header_position(row: Dict[str, any]):
    if row['page_num'] % 2 == 0:
        return np.nan
    return np.nan if row['date_type'] == 'header' or row['top'] > 250 else 'start_in_header_position'


def get_diff_with_prev(data_frame: pd.DataFrame):
    # check where there is a recto with no date header

    print('len data_frame:', len(data_frame))

    # list all page nums of rectos with date headers
    page_nums = list(data_frame[data_frame.date_type == 'header'].page_num)
    print('num page_nums:', len(page_nums))

    # compute the page_num distance with the previous date header page num
    diff_with_prev = [page_nums[i] - page_nums[i - 1] if i > 0 else np.nan for i in range(len(page_nums))]

    # get the row ids of the date headers
    header_idxs = data_frame[data_frame.date_type == 'header'].index
    print('num header_idxs:', len(header_idxs))

    # Next, map the page number differences to their corresponding row ids
    diff_map = {i: np.nan for i in range(len(data_frame))}
    for i, idx in enumerate(header_idxs):
        diff_map[idx] = diff_with_prev[i]
    print('num diff_map:', len(diff_map))

    # Add the page number differences to the new DataFrame
    data_frame['diff_with_prev'] = diff_map.values()


def rule_uses_window_size(rule: Callable) -> bool:
    if rule.__name__.startswith('rule_') is False:
        raise TypeError("Passed argument is not an imputation rule")
    if rule.__name__ in {'rule_month_1', 'rule_month_2'}:
        return True
    else:
        return False


def impute_data(date_classifier: DateClassifier, rule_func: Callable, date_region_data: Dict[str, List[any]],
                iterations: int = 1, window_size: int = 1):
    prev_months_filled = 0
    prev_days_filled = 0
    drd = copy.deepcopy(date_region_data)

    for iteration in range(iterations):
        change = 0
        new_month_nums = []
        new_day_nums = []
        for i in range(len(drd['month_num'])):
            cw = get_context_window(drd, i)

            if (cw.prev_inv is not None and cw.curr_inv != cw.prev_inv) \
                    or (cw.next_inv is not None and cw.curr_inv != cw.next_inv):
                new_month_nums.append(drd['month_num'][i])
                new_day_nums.append(drd['day_num'][i])
                continue

            if rule_uses_window_size(rule_func):
                month_num, day_num = rule_func(date_classifier, drd, i, window_size=window_size)
            else:
                month_num, day_num = rule_func(date_classifier, drd, i)
            new_month_nums.append(month_num)
            new_day_nums.append(day_num)

            if not date_classifier.is_same(month_num, cw.curr_month, is_num=False) or \
                    not date_classifier.is_same(day_num, cw.curr_day, is_num=False):
                # print(i, cw.curr_month, month_num, '\t', cw.curr_day, day_num)
                change += 1
        num_new_month_nums = len(date_classifier.filter_seq(new_month_nums))
        num_old_month_nums = len(date_classifier.filter_seq(drd['month_num']))
        months_filled = num_new_month_nums - num_old_month_nums
        days_filled = len(date_classifier.filter_seq(new_day_nums)) - len(date_classifier.filter_seq(drd['day_num']))

        print(f"iter {iteration}  window_size: {window_size}  changes: {change}  "
              f"months: {len(drd['month_num'])} {len(date_classifier.filter_seq(drd['month_num']))} "
              f"{len(date_classifier.filter_seq(new_month_nums))}"
              f"\tdays: {len(drd['day_num'])} {len(date_classifier.filter_seq(drd['day_num']))} "
              f"{len(date_classifier.filter_seq(new_day_nums))}"
              )

        if months_filled == prev_months_filled and days_filled == prev_days_filled and change == 0:
            break
        prev_months_filled = months_filled
        prev_days_filled = days_filled

        drd['month_num'] = [num for num in new_month_nums]
        drd['day_num'] = [num for num in new_day_nums]
    return drd


def apply_imputation_rules(data_frame: pd.DataFrame, rules: Union[Callable, List[Callable]],
                           date_classifier: DateClassifier, iterations: int = 1,
                           window_size: int = 3, debug: int = 0):
    if isinstance(rules, list) is False:
        rules = [rules]
    drd = read_date_text_regions_data(date_text_regions_frame=data_frame)
    if debug > 0:
        print(f'applying {len(rules)} imputation rules')
    for rule in rules:
        if debug > 0:
            print(f'\napplying imputation rule {rule.__name__}\n')
        drd = impute_data(date_classifier, rule, drd, iterations=iterations, window_size=window_size)
    return pd.DataFrame(drd)


def add_check(drd: Dict[str, List[any]], idx: int, reason: str):
    if pd.isna(drd['check'][idx]):
        drd['check'][idx] = reason
    else:
        drd['check'][idx] += f"|{reason}"
