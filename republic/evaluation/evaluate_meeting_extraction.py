from typing import Dict, Union, List
import random
import datetime
from elasticsearch import Elasticsearch

import republic.elastic.republic_retrieving as rep_es
import republic.parser.pagexml.pagexml_meeting_parser as meeting_parser
import republic.analyser.republic_inventory_analyser as inv_analyser
from republic.helper.metadata_helper import make_scan_urls
from republic.config.republic_config import base_config, set_config_inventory_num
from republic.model.republic_date import RepublicDate, get_next_workday, get_previous_workday
from republic.model.republic_meeting import Meeting, meeting_from_json


# old index
index = "republic_pagexml_meeting"
# new index
index = "pagexml_meeting"
doc_type = "meeting"

data_dir = "/Users/marijnkoolen/Data/Projects/REPUBLIC/"


def get_scan_urls(es: Elasticsearch, scan_num: int, inventory_num: int) -> Dict[str, str]:
    inv_config = set_config_inventory_num(base_config, inventory_num, data_dir, 'pagexml')
    inv_metadata = inv_analyser.get_inventory_metadata(es, inventory_num, inv_config)
    urls = make_scan_urls(inv_metadata, scan_num=scan_num)
    return urls


def num_month_days(month: int, year: int) -> int:
    if month == 2:
        return 29 if is_leap_year(year) else 28
    elif month in [4, 6, 9, 11]:
        return 30
    else:
        return 31


def is_leap_year(year: int) -> bool:
    return year % 4 == 0


def pick_random_date() -> RepublicDate:
    year = random.randint(1705, 1796)
    month = random.randint(1, 12)
    day = random.randint(1, num_month_days(month, year))
    if year == 1796 and month > 3:
        # 1796 only runs until 1 March
        month = random.randint(1, 3)
        if month == 3:
            day = 1
    return RepublicDate(year, month, day)


def get_meeting_by_date(es: Elasticsearch, date: RepublicDate) -> Union[None, Meeting]:
    # pre-session ID for old index
    doc_id = f'meeting-{date.isoformat()}-session-1'
    if es.exists(index=index, doc_type=doc_type, id=doc_id):
        response = es.get(index=index, doc_type=doc_type, id=doc_id)
        return meeting_from_json(response['_source'])
    else:
        return None


def get_sample_dates(sample_size: int) -> List[RepublicDate]:
    dates = []
    for i in range(1, sample_size + 1):
        date = pick_random_date()
        # 1725 and 1740 are missing in the PageXML for now
        while date.year in [1725, 1740]:
            date = pick_random_date()
        dates += [date]
    return dates
    # return [pick_random_date() for i in range(1, sample_size+1)]


def get_line_metadata(line: dict) -> Dict[str, Union[str, int, Dict[str, int]]]:
    line_id = line['id']
    parts = line_id.split('-')
    return {
        'line_id': line_id,
        'inv_num': int(parts[2]),
        'scan_num': int(parts[6]),
        'page_num': int(parts[8]),
        'col_index': int(parts[10]),
        'tr_index': int(parts[12]),
        'line_num': int(parts[14]),
        'coords': line['coords']
    }


def widen_region_box(coords: Dict[str, int]) -> Dict[str, int]:
    return {
        'left': coords['left'] - 100,
        'top': coords['top'] - 100,
        'width': coords['width'] + 200,
        'height': coords['height'] + 250,
    }


def get_next_meeting(es: Elasticsearch, sample_date: RepublicDate) -> Union[None, Meeting]:
    # start with next date
    next_date = get_next_workday(sample_date)
    if not next_date:
        return None
    next_meeting = get_meeting_by_date(es, next_date)
    return next_meeting


def get_previous_meeting(es: Elasticsearch, sample_date: RepublicDate) -> Union[None, Meeting]:
    # start with previous date
    prev_date = get_previous_workday(sample_date)
    if not prev_date:
        return None
    prev_meeting = get_meeting_by_date(es, prev_date)
    return prev_meeting


def check_sample_date(es: Elasticsearch, sample_date: RepublicDate):
    meeting = get_meeting_by_date(es, sample_date)
    date_info = {
        'date': sample_date.isoformat(),
        'weekday': sample_date.day_name,
        'is_work_day': sample_date.is_work_day(),
        'has_meeting': False,
        'match_string': None,
        'viewer_url': None,
        'iiif_url': None
    }
    if meeting:
        date_info['has_meeting'] = True
        if meeting.metadata['has_meeting_date_element']:
            for evidence in meeting.metadata['evidence']:
                if evidence['metadata_field'] == 'meeting_date':
                    date_info['match_string'] = evidence['matches'][0]['match_string']
        first_column = meeting.columns[0]
        first_line = first_column['textregions'][0]['lines'][0]
        for field in ['id', 'inventory_num', 'scan_num', 'page_num', 'column_index', 'textregion_index', 'line_index']:
            date_info[field] = first_line[field]
        urls = get_scan_urls(es, first_column['metadata']['scan_num'], first_column['metadata']['inventory_num'])
        date_info['viewer_url'] = urls['viewer_url']
        date_info['iiif_url'] = first_column['metadata']['iiif_url']
        if 'status' in meeting.metadata:
            date_info['meeting_status'] = meeting.metadata['status']
        else:
            date_info['meeting_status'] = meeting.metadata['date_shift_status']
    print(date_info['weekday'], sample_date.isoformat(),
          date_info['match_string'])
    next_meeting = get_next_meeting(es, sample_date)
    if next_meeting:
        #print('\tthere is a next meeting')
        date_info['next_meeting_match_string'] = None
        if next_meeting.metadata['has_meeting_date_element']:
            for evidence in next_meeting.metadata['evidence']:
                if evidence['metadata_field'] == 'meeting_date':
                    date_info['next_meeting_match_string'] = evidence['matches'][0]['match_string']
        first_column = next_meeting.columns[0]
        urls = get_scan_urls(es, first_column['metadata']['scan_num'], first_column['metadata']['inventory_num'])
        date_info['next_meeting_viewer_url'] = urls['viewer_url']
        date_info['next_meeting_iiif_url'] = first_column['metadata']['iiif_url']
        if 'status' in next_meeting.metadata:
            date_info['next_meeting_status'] = next_meeting.metadata['status']
        else:
            date_info['next_meeting_status'] = next_meeting.metadata['date_shift_status']
    prev_meeting = get_previous_meeting(es, sample_date)
    if prev_meeting:
        #print('\tthere is a previous meeting')
        date_info['prev_meeting_match_string'] = None
        if prev_meeting.metadata['has_meeting_date_element']:
            for evidence in prev_meeting.metadata['evidence']:
                if evidence['metadata_field'] == 'meeting_date':
                    date_info['prev_meeting_match_string'] = evidence['matches'][0]['match_string']
        first_column = prev_meeting.columns[0]
        urls = get_scan_urls(es, first_column['metadata']['scan_num'], first_column['metadata']['inventory_num'])
        date_info['prev_meeting_viewer_url'] = urls['viewer_url']
        date_info['prev_meeting_iiif_url'] = first_column['metadata']['iiif_url']
        if 'status' in prev_meeting.metadata:
            date_info['prev_meeting_status'] = prev_meeting.metadata['status']
        else:
            date_info['prev_meeting_status'] = prev_meeting.metadata['date_shift_status']
    if sample_date.is_rest_day() and not meeting and next_meeting:
        date_info['inventory_num'] = next_meeting.metadata['inventory_num']
        if 'status' in next_meeting.metadata:
            date_info['meeting_status'] = next_meeting.metadata['status']
        else:
            date_info['meeting_status'] = next_meeting.metadata['date_shift_status']
        first_column = next_meeting.columns[0]
        first_line = first_column['textregions'][0]['lines'][0]
        for field in ['id', 'inventory_num', 'scan_num', 'page_num', 'column_index', 'textregion_index', 'line_index']:
            date_info[field] = first_line[field]
        urls = get_scan_urls(es, first_column['metadata']['scan_num'], first_column['metadata']['inventory_num'])
        date_info['viewer_url'] = urls['viewer_url']
        date_info['iiif_url'] = first_column['metadata']['iiif_url']
    return date_info
