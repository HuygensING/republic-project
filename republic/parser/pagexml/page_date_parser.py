import copy
import json
from collections import defaultdict, Counter
from typing import Dict, List, Union

from fuzzy_search.search.phrase_searcher import FuzzyPhraseSearcher
from pagexml.model import physical_document_model as pdm
from pagexml.helper.pagexml_helper import regions_overlap

import republic.helper.pagexml_helper
import republic.parser.pagexml.republic_column_parser as column_parser
import republic.helper.pagexml_helper as pagexml_helper
from republic.helper.metadata_helper import get_tr_known_types
from republic.helper.metadata_helper import get_majority_line_class
from republic.helper.metadata_helper import get_line_class_dist
from republic.helper.metadata_helper import KNOWN_TYPES
from republic.helper.pagexml_helper import make_empty_tr, make_empty_line
from republic.model.inventory_mapping import get_inventory_by_id
from republic.model.republic_date import DateNameMapper
from republic.parser.logical.date_parser import get_date_token_cat
from republic.parser.logical.date_parser import get_session_date_lines_from_pages
from republic.parser.logical.date_parser import get_session_date_line_structures
from republic.parser.logical.date_parser import make_weekday_name_searcher
from republic.parser.pagexml.generic_pagexml_parser import copy_page
from republic.parser.pagexml.republic_page_parser import split_page_column_text_regions

from republic.classification.content_classification import DateRegionClassifier
from republic.model.republic_date_phrase_model import weekday_names, month_names

from republic.classification.content_classification import get_header_dates


REGION_EXCEPTIONS = {
    'NL-HaNA_1.01.02_3099_0423-text_region-3109-109-547-195': {'date_type': 'header', 'date': '1578-04-08'}
}


def load_date_region_classifier():
    weekday_map = {day_name: weekday_names[dtype][day_name] for dtype in weekday_names for day_name in
                   weekday_names[dtype]}
    month_name_map = {month_name: month_names[dtype][month_name] for dtype in month_names for month_name in
                      month_names[dtype]}
    return DateRegionClassifier(month_name_map=month_name_map, weekday_map=weekday_map)


def classify_page_date_regions(pages: List[pdm.PageXMLPage],
                               date_region_classifier: DateRegionClassifier) -> Dict[str, str]:
    date_tr_type_map = {}
    for page in pages:
        for tr in page.get_all_text_regions():
            if tr.has_type('date') is False:
                continue
            text = ' '.join([line.text for line in sorted(tr.lines) if line.text is not None])
            record = {
                'text': text,
                'bottom': tr.coords.bottom,
                'top': tr.coords.top,
                'page_num': page.metadata['page_num'],
                'num_lines': tr.stats['lines'],
                'num_words': tr.stats['words'],
                'left_indent': tr.coords.left - page.coords.left
            }
            date_type = date_region_classifier.classify_date_text(record, debug=0)
            date_tr_type_map[tr.id] = date_type
    return date_tr_type_map


def process_handwritten_columns(columns: List[pdm.PageXMLColumn], page: pdm.PageXMLPage):
    """Process all columns of a page and merge columns that are horizontally overlapping."""
    non_overlapping_columns = republic.helper.pagexml_helper.merge_overlapping_columns(columns, page)
    for col in non_overlapping_columns:
        col.text_regions = pagexml_helper.merge_overlapping_text_regions(col.text_regions, col)
    return non_overlapping_columns


def process_handwritten_text_regions(text_regions: List[pdm.PageXMLTextRegion], column: pdm.PageXMLColumn,
                                     debug: int = 0):
    return pagexml_helper.merge_overlapping_text_regions(text_regions, column, debug=debug)


def debug_print_page_trs(page: pdm.PageXMLPage, prefix: str, debug: int = 0):
    print(f"\n{prefix}")
    print(page.stats)
    for tr in page.get_all_text_regions():
        print(f"\n{tr.id} {get_tr_known_types(tr)}\thas session_date: {'session_date' in tr.metadata}")
        if debug > 0:
            for line in tr.lines:
                print(f"\t{line.id} line_class: {line.metadata['line_class']}")


def process_handwritten_page(page: pdm.PageXMLPage, weekday_name_searcher: FuzzyPhraseSearcher = None,
                             debug: int = 0):
    """Split and/or merge columns and overlapping text regions of handwritten
    resolution pages and correct line classes for session dates, attendance
    lists, date headers and paragraphs.

    If a weekday_name_searcher is passed, line classes will be updated to date if they contain
    a weekday name.
    """
    pagexml_helper.check_parentage(page)
    # print('BEFORE:', page.id, page.stats['lines'])
    page = copy_page(page)
    if page.stats['words'] == 0 or page.stats['lines'] == 0:
        return page
    try:
        page.columns = process_handwritten_columns(page.columns, page)
    except BaseException:
        print(f"page_date_parser.process_handwritten_page - error processing columns for page {page.id}")
        raise
    pagexml_helper.check_parentage(page)
    # print('AFTER:', page.id, page.stats['lines'])
    if page.stats['lines'] == 0:
        return page

    if debug > 0:
        debug_print_page_trs(page, "AFTER page_date_parser.process_handwritten_page "
                                   "-> process_handwritten_columns", debug=debug)
    for col in page.columns:
        # print(f'\n{col.id}\n')
        col.text_regions = process_handwritten_text_regions(col.text_regions, col, debug=debug)
    pagexml_helper.check_parentage(page)

    if debug > 0:
        debug_print_page_trs(page, "AFTER page_date_parser.process_handwritten_page "
                                   "-> process_handwritten_text_regions", debug=debug)
    page = split_page_column_text_regions(page, weekday_name_searcher=weekday_name_searcher,
                                          update_type=True, copy_page=False, debug=debug)
    if debug > 0:
        debug_print_page_trs(page, "AFTER page_date_parser.process_handwritten_page "
                                   "-> split_page_column_text_regions", debug=debug)
    pagexml_helper.check_parentage(page)
    return page


def get_record_info(record: Dict[str, any]):
    return {
        'text_region_id': record['text_region_id'],
        'line_ids': record['line_ids'],
        'date_type': record['date_type']
    }


def update_tr_type(tr: pdm.PageXMLTextRegion, record: Dict[str, any], debug: int = 0) -> None:
    """Update the text region type based on the date region record"""
    if debug > 1:
        print(f'\npage_date_parser.update_tr_type - record: {get_record_info(record)}')
        print(f"\ttr.type before update:{tr.type}")
    if record['date_type'] == 'start':
        tr.remove_type('header')
        tr.add_type('main')
        tr.add_type('date')
    elif record['date_type'] == 'header':
        tr.remove_type('main')
        tr.add_type('header')
        tr.add_type('date_header')
    else:
        tr.remove_type('date')
    if debug > 1:
        print(f"\ttr.type after update:{tr.type}")


def combine_stats(docs: List[pdm.PageXMLDoc]) -> Dict[str, int]:
    stats = defaultdict(int)
    for doc in docs:
        doc_stats = doc.stats
        for field in doc_stats:
            stats[field] += doc_stats[field]
    return stats


def compare_stats(stats1: Dict[str, int], stats2: Dict[str, int], fields: List[str] = None):
    if fields is None:
        fields1 = list(stats1.keys())
        fields2 = list(stats2.keys())
        fields = set(fields1 + fields2)
    for field in fields:
        if field not in stats1:
            raise ValueError()


def make_empty_line_tr(text_region_id: Union[str, List[str]], page: pdm.PageXMLPage,
                       empty_line_class: str = 'date') -> pdm.PageXMLTextRegion:
    """Make a text region with an empty line that stands in for a session start date line."""
    empty_tr = make_empty_tr(text_region_id, page)
    empty_line = make_empty_line(text_region_id)
    empty_line.set_derived_id(page.metadata['scan_id'])
    empty_line.add_type('inserted_empty')
    empty_line.metadata['line_class'] = empty_line_class
    empty_tr.lines.append(empty_line)
    empty_tr.set_as_parent(empty_tr.lines)
    return empty_tr


def find_date_region_record_lines(page: pdm.PageXMLPage, record: Dict[str, any],
                                  debug: int = 0) -> List[pdm.PageXMLTextLine]:
    """Find the lines on a page that overlap with the text region and line ids of a record"""
    record_lines = []
    if record['text_region_id'] is not None:
        if debug > 0:
            print(f"page_date_parser.find_date_region_record_lines - text_region_id is not None")
            print(f"\t{record['text_region_id']}")
        page_tr_ids = [tr.id for tr in page.get_all_text_regions()]
        if record['text_region_id'] in page_tr_ids:
            if debug > 0:
                print(f"page_date_parser.find_date_region_record_lines - text_region_id is in page_tr_ids")
            # scenario 1: the text region is literally the same region
            # action: copy all lines as the date region lines
            for tr in page.get_all_text_regions():
                if tr.id == record['text_region_id']:
                    record_lines.extend([line for line in tr.lines if line not in record_lines])
                    if debug > 1:
                        print(f"page_date_parser.find_date_region_record_lines - "
                              f"text_region_id {record['text_region_id']} is in page trs")
                        print(f"    moving {len(tr.lines)} lines")
                        for line in tr.lines:
                            print(f"\tmoving line {line.id}")
                    if len(record_lines) == 0:
                        raise ValueError(f"matching text region id {record['text_region_id']} has no lines")
        else:
            if debug > 0:
                print(f"page_date_parser.find_date_region_record_lines - text_region_id is not in page_tr_ids")
            # scenario 2: the text region is not literally the same as any region in the page
            # action: create a dummy region based on the coordinates in the ID and select
            # lines contained by the region
            record_tr = make_empty_tr(record['text_region_id'], page)
            if debug > 0:
                print(f"\tmade empty tr - record_tr.coords.box: {record_tr.coords.box}")
            for page_tr in page.get_all_text_regions():
                for line in page_tr.lines:
                    if debug > 0:
                        print(f"\t{line.coords.box}\t{regions_overlap(record_tr, line, threshold=0.5)}\t{line.text}")
                    if regions_overlap(record_tr, line, threshold=0.5) and line not in record_lines:
                        record_lines.append(line)
            if debug > 0:
                print(f'    number of matching lines found: {len(record_lines)}')
                if len(record_lines) == 0:
                    print(f"\tNO matching line found")
            if len(record_lines) == 0:
                if record['text_region_id'] in REGION_EXCEPTIONS:
                    empty_line_tr = make_empty_line_tr(record['text_region_id'], page)
                    page.add_child(empty_line_tr)
                    record_lines.append(empty_line_tr.lines[0])
                    return record_lines
                for tr in page.get_all_text_regions():
                    print(f" page {page.id} has tr {tr.id} with {len(tr.lines)} lines")
                raise ValueError(f"no overlapping lines found for text region id {record['text_region_id']}")
            if debug > 1:
                print(f"page_date_parser.find_date_region_record_lines - "
                      f"text_region_id {record['text_region_id']} is not in page trs")
                print(f"    moving {len(record_lines)} lines from other text regions")
                for line in record_lines:
                    print(f"\tline: {line.id}\t{line.text}")
    if len(record['line_ids']) > 0:
        if debug > 0:
            print(f"page_date_parser.find_date_region_record_lines - line_ids is not None")
        # scenario 3: there is no text region id, so there should be one or more line IDs
        # action: select the lines with the corresponding IDs from the page
        record_lines.extend([line for line in page.get_lines() if line.id in record['line_ids'] and
                             line not in record_lines])
        page_line_ids = [line.id for line in page.get_lines()]
        missing_ids = [line_id for line_id in record['line_ids'] if line_id not in page_line_ids]
        if len(missing_ids) > 0:
            merged_lines = 0

            missing_record_lines = []
            for missing_id in missing_ids:
                # print('missing_id:', missing_id)
                line_coords = pagexml_helper.make_coords_from_doc_id(missing_id)
                record_line = pdm.PageXMLTextRegion(coords=line_coords)
                missing_record_lines.append(record_line)
            missing_tr_coords = pdm.parse_derived_coords(missing_record_lines)
            missing_tr = pdm.PageXMLTextRegion(coords=missing_tr_coords)
            for page_line in page.get_lines():
                # print(f"\t{page_line.coords.box}\t{regions_overlap(page_line, record_line, threshold=0.5)}"
                #       f"\t{page_line.text}")
                if regions_overlap(missing_tr, page_line):
                    if page_line not in record_lines:
                        record_lines.append(page_line)
                    else:
                        merged_lines += 1
            """
            if len(record['line_ids']) > len(record_lines) + merged_lines:
                print(f"page_date_parser.find_record_lines - line_ids: {record['line_ids']}")
                print(f"page_date_parser.find_record_lines - lines: {[line.id for line in record_lines]}")
                raise ValueError(f"more 'line_ids' ({len(record['line_ids'])}) then "
                                 f"the number of record_lines ({len(record_lines)})")
            """
        if debug > 1:
            print(f"page_date_parser.find_date_region_record_lines - "
                  f"line_ids {record['line_ids']} in record")
            print(f"\tmoving {len(record_lines)} lines from other text regions")
    return record_lines


def check_date_region_record_ids(record: Dict[str, any]):
    error = None
    if 'line_ids' not in record:
        error = KeyError("record must contain a 'line_ids' property.")
    if isinstance(record['line_ids'], list) is False:
        error = KeyError(f"record['line_ids'] must be a list, not {record['line_ids']}.")
    if record['text_region_id'] is None and len(record['line_ids']) == 0:
        error = ValueError(f"'text_region_id' and 'line_ids' cannot both be empty")
    if error:
        print(f"page_date_parser.check_record_ids - invalid record:")
        print(json.dumps(record, indent=4))
        raise error


def check_date_region_records_ids(records: List[Dict[str, any]]):
    for record in records:
        check_date_region_record_ids(record)


def has_duplicate_lines(record_lines: List[pdm.PageXMLTextLine]):
    line_freq = Counter([line for line in record_lines])
    if max(line_freq.values()) > 1:
        print(f"page_date_parser.has_duplicate_lines - duplicate record lines detected")
        for line, freq in line_freq.items():
            if freq > 1:
                print(f"    {line.id}\t{line.text}")
        return True
    return False


def sort_date_trs_and_lines(page: pdm.PageXMLPage, records: List[Dict[str, any]],
                            debug: int = 0, make_copy: bool = True) -> List[pdm.PageXMLTextRegion]:
    all_trs = []
    check_date_region_records_ids(records)
    records = [copy.deepcopy(record) for record in records if record['page_num'] == page.metadata['page_num']]
    # step 0: make sure original page does not change
    dummy_page = copy_page(page) if make_copy else page
    # step 1: find lines associated with each date region record
    for record in records:
        record['lines'] = find_date_region_record_lines(dummy_page, record, debug=debug)
        if has_duplicate_lines(record['lines']):
            raise ValueError(f"record_lines cannot have duplicates")
    record_line_set = set([line for record in records for line in record['lines']])
    # step 2: remove date lines from current text regions
    for tr in dummy_page.get_all_text_regions():
        tr_lines = [line for line in tr.lines]
        for line in tr_lines:
            if line in record_line_set:
                # print('removing line from regular trs:', line.id)
                tr.lines.remove(line)
                if len(tr.lines) > 0:
                    tr.coords = pdm.parse_derived_coords(tr.lines)
                    tr.set_derived_id(tr.metadata['scan_id'])
        if len(tr.lines) > 0:
            all_trs.append(tr)
    # step 3: create new text regions for each date record
    for record in records:
        date_tr = derive_text_region_from_date_record(record)
        if debug > 1:
            print('page_date_parser.sort_date_trs_and_lines - record:', record)
            print('    adding date tr:', date_tr.id, get_tr_known_types(date_tr))
        # for line in date_tr.lines:
        #     print(f"\t{line.id}")
        all_trs.append(date_tr)

    # step 4: split text regions that have a vertical gap because a line has been removed
    #         and moved to a date text region
    new_trs = []
    for tr in all_trs:
        split_trs = column_parser.split_text_region_on_vertical_gap(tr, update_type=False, debug=0)
        new_trs.extend(split_trs)
    return new_trs


def derive_text_region_from_date_record(record: Dict[str, any],
                                        debug: int = 0) -> pdm.PageXMLTextRegion:
    """Generate a text_region of type date based on a date record."""
    lines = record['lines']
    for line in lines:
        if line.metadata['line_class'] != 'attendance':
            line.metadata['line_class'] = 'date'
    metadata = None
    if len(lines) == 0:
        print(f'page_date_parser.derive_text_region_from_date_record - record: {get_record_info(record)}')
        raise IndexError(f"lines derived from date record cannot be empty.")
    try:
        coords = pdm.parse_derived_coords(lines)
    except AttributeError:
        print('page_date_parser.derive_text_region_from_date_record - record:\n', record)
        for line in lines:
            print('\tline:', line)
        raise
    if metadata is None:
        metadata = copy.deepcopy(lines[0].parent.metadata)
        if 'text_region_id' in metadata:
            del metadata['text_region_id']
    date_tr = pdm.PageXMLTextRegion(metadata=metadata, coords=coords, lines=lines)
    date_tr.set_as_parent(lines)
    if 'scan_id' not in metadata:
        print(f'page_date_parser.derive_text_region_from_date_record - record: {get_record_info(record)}')
        raise KeyError(f"no 'scan_id' in metadata derived from date record element(s).")
    date_tr.set_derived_id(metadata['scan_id'])
    if debug > 0:
        print("\npage_date_parser.derive_text_region_from_date_record:")
        print(f"    record: {get_record_info(record)}")
        print(f"    date_tr: {date_tr.id}")
        for line in date_tr.lines:
            print(f"\tline {line.id} has parent {line.parent.id}")
    update_tr_type(date_tr, record, debug=debug)
    date_tr.metadata['session_start'] = True if record['date_type'] == 'start' else False
    date_tr.metadata['date_type'] = record['date_type']
    date_tr.metadata['session_date'] = record['date']
    date_tr.metadata['second_session'] = record['second_session']
    if debug > 0:
        print(f'\npage_date_parser.derive_text_region_from_date_record - date_tr: {date_tr.id}')
        print(f"\tmetadata['session_date']: {date_tr.metadata['session_date']}")
    return date_tr


def sort_trs_by_type(trs: List[pdm.PageXMLTextRegion], debug: int = 0) -> Dict[str, List[pdm.PageXMLTextRegion]]:
    """Sort a list of text regions into a dictionary with a list of text regions per type.

    Types should be marginalia, date, attendance, resolution"""
    trs_by_type = defaultdict(list)
    for tr in trs:
        tr_known_types = get_tr_known_types(tr)
        if len(tr_known_types) > 1 and 'noise' in tr_known_types:
            tr.remove_type(KNOWN_TYPES)
            tr.add_type('noise')
        tr_known_types = get_tr_known_types(tr)
        line_class = None
        if len(tr_known_types) == 0:
            line_class = get_majority_line_class(tr.lines)
            if line_class is not None:
                tr.add_type(line_class)
                tr_known_types = get_tr_known_types(tr)
        if len(tr_known_types) == 0:
            print(f"page_date_parser.sort_trs_by_type - tr {tr.id} has no known type:")
            print(f"    known_types: {KNOWN_TYPES}")
            print(f"    tr.type: {tr.type}")
            print(f"    line_class: {line_class}")
            print(f"    line_class_dist: {get_line_class_dist(tr.lines)}")
            for line in tr.lines:
                print(f"\tline {line.id}\t{line.text}\ttext: {line.text}")
            raise TypeError(f"tr {tr.id} has no known type")
        elif len(tr_known_types) > 1:
            print(f"page_date_parser.sort_trs_by_type - tr {tr.id} has multiple known types:")
            print(f"    known_types: {KNOWN_TYPES}")
            print(f"    tr.type: {tr.type}")
            for line in tr.lines:
                print(f"\tline {line.id}\t{line.text}\ttext: {line.text}")
            raise TypeError(f"tr {tr.id} has multiple known types")
        added = False
        for tr_type in KNOWN_TYPES:
            if tr.has_type(tr_type):
                trs_by_type[tr_type].append(tr)
            added = True
        if added is False:
            print("page_date_parser.sort_trs_by_type - ")
            print(f'\ttr {tr.id} not added, because it has no known type - tr.type: {tr.type}')
    total_by_type = sum([len(trs_by_type[tr_type]) for tr_type in trs_by_type])
    if total_by_type != len(trs):
        print("page_date_parser.sort_trs_by_type:")
        print(f"    number of initial trs: {len(trs)}")
        print(f"    number of trs by type: {total_by_type}")
        for tr_type in trs_by_type:
            for tr in trs_by_type[tr_type]:
                print(f"\t{tr_type}\t{tr.id}")
        for tr in trs:
            if any([tr.id in trs_by_type[tr_type] for tr_type in trs_by_type]) is False:
                print(f"\tmissing tr: {tr.id} ({tr.type})")
        raise ValueError(f"number of initial trs {len(trs)} unequal to number of trs by type {total_by_type}")
    return trs_by_type


def update_page_with_date_info(page: pdm.PageXMLPage, records: List[Dict[str, any]],
                               debug: int = 0) -> pdm.PageXMLPage:
    # update lines of date regions and lines to type 'date'
    # update text regions to type date and main if they are a session start
    # update text regions to type date_header and header if they are a session start
    page = copy_page(page)
    for tr in page.get_all_text_regions():
        has_empty = False
        for line in tr.lines:
            if line.text is None: # or line.metadata['line_class'] != 'empty':
                has_empty = True
                tr.lines.remove(line)
        if has_empty is True:
            tr.set_derived_id(page.metadata['scan_id'])
    orig_stats = page.stats
    if debug > 0:
        debug_print_page_trs(page, "BEFORE page_date_parser.update_page_with_date_info - "
                                   "sort_date_trs_and_lines", debug=debug)
    new_trs = sort_date_trs_and_lines(page, records, make_copy=False, debug=debug)
    line_id_freq = Counter([line.id for tr in new_trs for line in tr.lines])
    if max(line_id_freq.values()) > 1:
        has_duplicate_lines([line for tr in new_trs for line in tr.lines])
        double_ids = [line_id for line_id, freq in line_id_freq.items() if freq > 1]
        if len(double_ids) > 0:
            print(f"page_date_parser.update_page_with_date_info - duplicate lines in new_trs:")
            for tr in new_trs:
                for line in tr.lines:
                    if line.id in double_ids:
                        print(f"\tline {line.id} in tr {tr.id} with type {get_tr_known_types(tr)}")
            raise ValueError("duplicate lines in new_trs after sort_date_trs_and_lines")

    trs_by_type = sort_trs_by_type(new_trs)
    # for tr_type in trs_by_type:
    #     print(tr_type, [tr.id for tr in trs_by_type[tr_type]])
    cols = []
    metadata = copy.deepcopy(page.columns[0].metadata)
    for tr_type in trs_by_type:
        coords = pdm.parse_derived_coords(trs_by_type[tr_type])
        col = pdm.PageXMLColumn(metadata=metadata, coords=coords, text_regions=trs_by_type[tr_type])
        if debug > 0:
            print(f"page_date_parser.update_page_with_date_info - column grouping for trs of type: {tr_type}")
            print(f"    coords: {coords.box}")
            print(f"    col.stats: {col.stats}")
            for tr in trs_by_type[tr_type]:
                print(f"\ttr: {tr.id} {get_tr_known_types(tr)}")
                # print(f"\ttr: {tr.id} {get_tr_known_types(tr)}")
            print()
        col.set_derived_id(metadata['scan_id'])
        cols.append(col)
        # print(f"Adding column to new_page: {col.id}\n")
    # print(f'\nNumber of columns: {len(cols)}')
    new_page = pdm.PageXMLPage(doc_id=page.id, metadata=copy.deepcopy(page.metadata),
                               doc_type=copy.deepcopy(page.type), coords=copy.deepcopy(page.coords),
                               columns=cols)

    if debug > 1:
        debug_print_page_trs(new_page, "BEFORE page_date_parser.update_page_with_date_info - "
                                       "process_handwritten_page", debug=debug)
    # split and sort columns and text regions
    new_page = process_handwritten_page(new_page, debug=debug)
    if debug > 1:
        print("AFTER page_date_parser.process_handwritten_page")
        print(new_page.stats)
    for tr in new_page.get_all_text_regions():
        if 'session_date' in tr.metadata and tr.has_type('date') is False:
            del tr.metadata['session_start']
            del tr.metadata['session_date']
            del tr.metadata['second_session']
        if debug > 1:
            print(tr.id, get_tr_known_types(tr), 'session_date' in tr.metadata)

    new_stats = new_page.stats
    inserted_empties = [line for line in new_page.get_lines() if line.has_type('inserted_empty')]
    for field in ['lines', 'words']:
        max_diff = len(inserted_empties) if field == 'lines' else 0
        if orig_stats[field] != new_stats[field] - max_diff:
            print(f"page_date_parser.update_page_with_date_info - unequal {field} stats:")
            print(f"\toriginal page stats: {orig_stats}")
            print(f"\tupdated page stats: {new_stats}")
            for line in sorted(new_page.get_lines()):
                print(f"\tnew_page line: {line.id} {line.has_type('inserted_empty')}")
            raise ValueError(f"unequal number of {field} in original page ({orig_stats[field]}) and "
                             f"updated page ({new_stats[field]}).")
    return new_page


def make_inventory_date_name_mapper(inv_id: str, pages: List[pdm.PageXMLPage],
                                    filter_date_starts: bool = True, date_tr_type_map: Dict[str, str] = None,
                                    debug: int = 0):
    """Return a date name mapper for a given inventory that returns likely date representations
    for a given date, based on the date format found in the pages of the inventory."""
    inv_meta = get_inventory_by_id(inv_id)
    date_token_cat = get_date_token_cat(inv_num=inv_meta['inventory_num'], ignorecase=True)
    session_date_lines = get_session_date_lines_from_pages(pages, filter_date_starts=filter_date_starts,
                                                           date_tr_type_map=date_tr_type_map, debug=debug)
    date_line_structures = get_session_date_line_structures(session_date_lines, date_token_cat,
                                                            inv_meta['inventory_id'], debug=debug)
    if debug > 0:
        print("page_date_parser.make_inventory_date_name_mapper - date_line_structures:")
        print(date_line_structures)
    try:
        date_mapper = DateNameMapper(inv_meta, date_line_structures)
    except Exception:
        print(f"Error creating DateNameMapper for inventory {inv_meta['inventory_num']}")
        print(f"with date_line_structure:", date_line_structures)
        print(f"with session_date_lines:", [line.text for line in session_date_lines])
        raise
    return date_mapper


def process_handwritten_pages(inv_id: str, pages: List[pdm.PageXMLPage],
                              filter_date_starts: bool = False, date_tr_type_map: Dict[str, str] = None,
                              ignorecase: bool = True, debug: int = 0):
    date_mapper = make_inventory_date_name_mapper(inv_id, pages, filter_date_starts=filter_date_starts,
                                                  date_tr_type_map=date_tr_type_map, debug=debug)
    config = {'ngram_size': 3, 'skip_size': 1, 'ignorecase': ignorecase, 'levenshtein_threshold': 0.8}
    weekday_name_searcher = make_weekday_name_searcher(date_mapper, config)
    new_pages = [process_handwritten_page(page, weekday_name_searcher=weekday_name_searcher,
                                          debug=0) for page in pages]
    return new_pages


def add_page_ids_to_trs(pages: List[pdm.PageXMLPage]):
    for page in pages:
        for tr in page.get_all_text_regions():
            if 'page_id' not in tr.metadata:
                tr.metadata['page_id'] = page.id
    return None


def preprocess_handwritten_pages(inv_id: str, pages: List[pdm.PageXMLPage],
                                 ignorecase: bool = False):

    config = {
        'ngram_size': 3,
        'skip_size': 1,
        'ignorecase': ignorecase,
        'levenshtein_threshold': 0.8
    }

    inv_meta = get_inventory_by_id(inv_id)
    inv_num = inv_meta['inventory_num']

    date_region_classifier = load_date_region_classifier()

    add_page_ids_to_trs(pages)
    pages.sort(key=lambda page: page.id)
    date_trs = get_header_dates(pages)
    print(f"inv {inv_num}  step 0: {len(date_trs)}")
    date_tr_type_map = classify_page_date_regions(pages, date_region_classifier)

    pages = process_handwritten_pages(inv_id, pages, filter_date_starts=True,
                                      date_tr_type_map=date_tr_type_map,
                                      ignorecase=ignorecase, debug=0)
    date_trs[inv_num] = get_header_dates(pages)
    print(f"inv {inv_num}  step 1: {len(date_trs[inv_num])}")

    date_tr_type_map = classify_page_date_regions(pages, date_region_classifier)

    date_mapper = get_inventory_date_mapper(inv_meta, pages,
                                            filter_date_starts=True,
                                            date_tr_type_map=date_tr_type_map,
                                            ignorecase=ignorecase, debug=0)

    weekday_name_searcher = make_weekday_name_searcher(date_mapper, config)
    pages = [process_handwritten_page(page, weekday_name_searcher=weekday_name_searcher,
                                      debug=0) for page in pages]

    print(f"inv {inv_num}  step 2: {len(date_trs[inv_num])}")
    return pages


def get_inventory_date_mapper(inv_metadata: Dict[str, any], pages: List[pdm.PageXMLPage],
                              filter_date_starts: bool = False, date_tr_type_map: Dict[str, str] = None,
                              ignorecase: bool = True, debug: int = 0):
    date_token_cat = get_date_token_cat(inv_num=inv_metadata['inventory_num'], ignorecase=ignorecase)
    session_date_lines = get_session_date_lines_from_pages(pages, filter_date_starts=filter_date_starts,
                                                           date_tr_type_map=date_tr_type_map, debug=debug)
    if len(session_date_lines) == 0:
        print(f"WARNING page_date_parser.get_inventory_date_mapper - No session date lines found for "
              f"inventory {inv_metadata['inventory_num']} with {len(pages)} pages")
        return None
    date_line_structures = get_session_date_line_structures(session_date_lines,
                                                            date_token_cat, inv_metadata['inventory_id'])
    if debug > 1:
        print(f"page_date_parser.get_inventory_date_mapper - date_line_structures:\n{date_line_structures}")
    """
    if 'weekday_name' not in [element[0] for element in date_line_structure]:
        print('WARNING - missing weekday_name in date_line_structure for inventory', inv_metadata['inventory_num'])
        return None
    """

    return DateNameMapper(inv_metadata, date_line_structures)