import io
import json
from typing import Dict, List

import numpy as np
import pandas as pd
import requests
from pandas.errors import ParserError

from republic.model.inventory_mapping import get_inventory_by_num


def download_inv_sheet(inv_map: Dict[str, any]):
    dtype = {
        'unrecognized_start_verso': str,
        'unrecognized_start_recto': str,
        'unrecognized_header': str
    }
    url = f"{inv_map['base_url']}/{inv_map['file_id']}/export?gid={inv_map['sheet_id']}&exportFormat=tsv"
    response = requests.get(url)
    if response.status_code != 200:
        print(f'download_inv_sheet received response.status_code {response.status_code} for url {url}')
        raise ValueError(response.text)
    try:
        inv_df = pd.read_csv(io.StringIO(response.text), sep='\t', dtype=dtype)
    except ParserError:
        print(f"Error parsing inv_sheet for inv {inv_map['inv_num']}")
        print(f"response.text:\n{response.text}")
        raise
    inv_df.inv_num = inv_map['inv_num']
    inv_df = inv_df[inv_df.date_type != 'no_date']
    inv_df = inv_df[inv_df.scan_num.isna() == False]
    return inv_df.rename(columns={'id': 'text_region_id'})


def make_viewer_url(record: Dict[str, any]):
    scan_num_string = (4 - len(str(record['scan_num']))) * '0' + str(record['scan_num'])
    record['scan_id'] = f"NL-HaNA_1.01.02_{record['inv_num']}_{scan_num_string}"
    # print(record['scan_num'], record['scan_id'])
    base_viewer_url = "https://www.nationaalarchief.nl/onderzoeken/archief/1.01.02/invnr"
    # scan_id = f"NL-HaNA_1.01.02_{record['inv_num']}_{record['scan_num']}"
    return f"{base_viewer_url}/{record['inv_num']}/file/{record['scan_id']}"


def get_missing_rows(inv_df: pd.DataFrame, missing_cols: List[str]):
    missing_dfs = []
    for col in missing_cols:
        missing_df = inv_df[inv_df[col].isna() == False]
        missing_dfs.append(missing_df)
    return pd.concat(missing_dfs)


def get_second_session(record: Dict[str, any]):
    if pd.isna(record['session_day_num']) == False:
        return 1 if record['session_day_num'].endswith('-2') else 0
    return 0


def get_day_num(missing_value: any):
    if isinstance(missing_value, str):
        try:
            return int(missing_value.split('/')[0].split('-')[0])
        except ValueError:
            print(f"date_imputation.get_day_num - invalid day_num: {missing_value}")
            raise
    return int(missing_value)


def get_month_num(record: Dict[str, any]):
    if pd.isna(record['session_day_num']) == False and '/' in record['session_day_num']:
        return int(record['session_day_num'].split('-')[0].split('/')[-1])
    else:
        return record['month_num']


def complete_record(record: Dict[str, any], inv_meta: Dict[str, any]):
    if 'unrecognized_type' not in record:
        record['unrecognized_type'] = np.nan
    if 'session_day_num' not in record:
        record['session_day_num'] = np.nan
    if 'page_num' not in record or pd.isna(record['page_num']):
        offset = 2 if record['unrecognized_type'].endswith('verso') else 1
        page_num = record['scan_num'] * 2 - offset
        if abs(page_num - record['page_num']) != 0:
            print('date_imputation.complete_record - inconsistency in data')
            print(json.dumps(record, indent=4))
            raise
        record['page_num'] = record['scan_num'] * 2 - offset

    if pd.isna(record['session_day_num']) == False:
        try:
            record['day_num'] = get_day_num(record['session_day_num'])
        except ValueError:
            print('date_imputation.complete_record - error parsing session_day_num:')
            print(json.dumps(record, indent=4))
            raise
    else:
        int(record['day_num'])

    record['second_session'] = get_second_session(record)
    record['line_ids'] = np.nan
    if pd.isna(record['day_num']):
        print('NO DAY_NUM:', record)
        return
    if pd.isna(record['month_num']):
        print('NO MONTH_NUM:', record)

    record['month_num'] = get_month_num(record)
    try:
        record['year'] = int(record['year'])
    except ValueError:
        print('date_imputation.complete_record - error casting year to int:')
        print(json.dumps(record, indent=4))
        raise
    if record['year'] < inv_meta['year_start'] or record['year'] > inv_meta['year_end']:
        print('date_imputation.complete_record - invalid year:')
        print(json.dumps(record, indent=4))
        raise ValueError(f"Invalid year {record['year']}")
    if pd.isna(record['page_num']):
        print('NO PAGE_NUM:', record)
    record['page_num'] = int(record['page_num'])
    if pd.isna(record['unrecognized_type']) == False:
        record['date_type'] = 'header' if record['unrecognized_type'].endswith('header') else 'start'
    record['scan_viewer_url'] = make_viewer_url(record)


def get_dates_missing_merge(inv_df: pd.DataFrame):
    inv_df = inv_df[inv_df.date_type != 'no_date']
    inv_df['unrecognized_type'] = np.nan
    inv_df['session_day_num'] = np.nan

    records = inv_df.to_dict('records')
    has_inconsistencies = False
    for record in records:
        if isinstance(record['unrecognized_start_verso'], str):
            if record['page_num'] % 2 == 1:
                print('date_imputation.complete_record - inconsistent missing date information:')
                print(f"    unrecognized_start_verso: {record['unrecognized_start_verso']}")
                print(f"    page_num: {record['page_num']}")
                has_inconsistencies = True
        if isinstance(record['unrecognized_start_recto'], str):
            if record['page_num'] % 2 == 0:
                print('date_imputation.complete_record - inconsistent missing date information:')
                print(f"    unrecognized_start_recto: {record['unrecognized_start_recto']}")
                print(f"    page_num: {record['page_num']}")
                has_inconsistencies = True
    if has_inconsistencies is True:
        raise ValueError("inconsistent missing date information")

    missing_cols = [col for col in inv_df.columns if 'unrecognized' in col]

    missing_df = get_missing_rows(inv_df, missing_cols)
    missing_df['page_num'] = np.nan
    non_missing_df = inv_df[inv_df.day_num.isna() == False]

    dates_df = non_missing_df[non_missing_df.check != 'to_merge_with_prev_start']
    merge_df = inv_df[inv_df.check == 'to_merge_with_prev_start']
    print('missing_df len:', len(missing_df))
    print('dates_df len:', len(dates_df))
    print('merge_df len:', len(merge_df))
    return dates_df, missing_df, merge_df


def derive_page_num(row: Dict[str, any]):
    if row['unrecognized_type'].endswith('verso'):
        return row['scan_num'] * 2 - 2
    else:
        return row['scan_num'] * 2 - 1


def missing_to_long(missing_df: pd.DataFrame):
    select_cols = [
        'inv_num', 'text_region_id', 'scan_num', 'page_num',
        'year', 'month_num', 'day_num', 'second_session',
        'check', 'date_type'
    ]

    missing_cols = [col for col in missing_df.columns if 'unrecognized' in col]

    missing_long = missing_df.melt(id_vars=select_cols, value_vars=missing_cols,
                                   var_name='unrecognized_type', value_name='session_day_num_list')
    print('step 1:', missing_long.columns)

    missing_long['day_num'] = np.nan
    missing_long = missing_long[missing_long.session_day_num_list.isna() == False]
    print('step 2:', missing_long.columns)
    missing_long['session_day_num'] = missing_long.session_day_num_list.str.split(', ')
    print('step 3:', missing_long.columns)
    missing_long = missing_long.explode('session_day_num')
    missing_long['page_num'] = missing_long.apply(derive_page_num, axis=1)
    return missing_long


def get_records(dates_df, missing_long):
    complete_data = []

    inv_meta = {inv_num: get_inventory_by_num(inv_num) for inv_num in dates_df.inv_num.unique()}
    select_cols = [
        'inv_num', 'text_region_id', 'scan_num', 'page_num', 'year', 'month_num', 'day_num', 'second_session',
        'check', 'date_type', 'unrecognized_type', 'session_day_num'
    ]

    print('\nCompleting records with no missing col\n')
    for record in dates_df[select_cols].to_dict('records'):
        complete_record(record, inv_meta[record['inv_num']])
        complete_data.append(record)

    missing_data = []
    print(f'\nCompleting records with missing col\n')
    missing_records = missing_long[select_cols].to_dict('records')
    for record in sorted(missing_records, key=lambda r: (r['scan_num'], r['session_day_num'])):
        # print('BEFORE:', record)
        complete_record(record, inv_meta[record['inv_num']])
        record['text_region_id'] = None
        missing_data.append(record)

    missing_df = pd.DataFrame(missing_data)
    complete_df = pd.DataFrame(complete_data)

    return pd.concat([missing_df, complete_df]).sort_values(['page_num', 'day_num'])
