import copy
from collections import defaultdict
from typing import Dict, List

from fuzzy_search.search.phrase_searcher import FuzzyPhraseSearcher
from pagexml.model import physical_document_model as pdm

import republic.parser.pagexml.republic_column_parser as column_parser
import republic.helper.pagexml_helper as pagexml_helper
from republic.helper.metadata_helper import get_tr_known_types
from republic.helper.metadata_helper import get_majority_line_class
from republic.helper.metadata_helper import get_line_class_dist
from republic.helper.metadata_helper import KNOWN_TYPES
from republic.model.inventory_mapping import get_inventory_by_id
from republic.model.republic_date import DateNameMapper
from republic.parser.logical.date_parser import get_date_token_cat, get_session_date_lines_from_pages, \
    get_session_date_line_structure
from republic.parser.logical.date_parser import get_session_date_lines_from_pages
from republic.parser.logical.date_parser import get_session_date_line_structure
from republic.parser.logical.date_parser import make_week_day_name_searcher
from republic.parser.pagexml.generic_pagexml_parser import copy_page
from republic.parser.pagexml.republic_page_parser import split_page_column_text_regions

from republic.classification.content_classification import DateRegionClassifier
from republic.model.republic_date_phrase_model import week_day_names, month_names

from republic.classification.content_classification import get_header_dates


def load_date_region_classifier():
    weekday_map = {day_name: week_day_names[dtype][day_name] for dtype in week_day_names for day_name in
                   week_day_names[dtype]}
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
    merge_sets = column_parser.find_overlapping_columns(columns)
    # print(merge_sets)
    merge_cols = {col for merge_set in merge_sets for col in merge_set}
    non_overlapping_cols = [col for col in columns if col not in merge_cols]
    for merge_set in merge_sets:
        # print("MERGING OVERLAPPING COLUMNS:", [col.id for col in merge_set])
        merged_col = pagexml_helper.merge_columns(merge_set, "temp_id", merge_set[0].metadata)
        merged_col.set_derived_id(page.id)
        merged_col.set_parent(page)
        non_overlapping_cols.append(merged_col)
    return non_overlapping_cols


def process_handwritten_text_regions(text_regions: List[pdm.PageXMLTextRegion], column: pdm.PageXMLColumn,
                                     debug: int = 0):
    """Process all text regions of a columns and merge regions that are overlapping."""
    if debug > 3:
        print(f'page_date_parser.process_handwritten_text_regions - start with {len(text_regions)} trs')
    non_overlapping_trs = []
    for tr in text_regions:
        pagexml_helper.check_parentage(tr)
    merge_sets = pagexml_helper.get_overlapping_text_regions(text_regions, overlap_threshold=0.5)
    assert sum(len(ms) for ms in merge_sets) == len(text_regions), "merge_sets contain more text regions than given"
    if debug > 3:
        for merge_set in merge_sets:
            print('page_date_parser.process_handwritten_text_regions - merge_set size:', len(merge_set))
    for merge_set in merge_sets:
        if len(merge_set) == 1:
            tr = merge_set.pop()
            if debug > 3:
                print(f'page_date_parser.process_handwritten_text_regions - '
                      f'adding tr at index {len(non_overlapping_trs)}:', tr.id)
            pagexml_helper.check_parentage(tr)
            non_overlapping_trs.append(tr)
            continue
        # print("MERGING OVERLAPPING TEXTREGION:", [tr.id for tr in merge_set])
        lines = [line for tr in merge_set for line in tr.lines]
        if len(lines) == 0:
            if debug > 3:
                print('page_date_parser.process_handwritten_text_regions - '
                      'no lines for merge_set of text regions with ids:',
                      [tr.id for tr in text_regions])
            coords = pdm.parse_derived_coords(list(merge_set))
        else:
            coords = pdm.parse_derived_coords(lines)
        # Copy metadata from first tr
        # add fields from other trs if the first one doesn't have them
        # (avoids losing information like session_date)
        metadatas = [tr.metadata for tr in merge_set]
        metadata = copy.deepcopy(metadatas.pop())
        for extra_metadata in metadatas:
            for field in extra_metadata:
                if field not in metadata:
                    metadata[field] = extra_metadata[field]
        if debug > 2:
            print('page_date_parser.process_handwritten_text_regions - merged_tr.metadata:', metadata.keys())
        merged_tr = pdm.PageXMLTextRegion(doc_id="temp_id", metadata=metadata,
                                          coords=coords, lines=lines)
        # print(merged_tr)
        merged_tr.set_derived_id(column.metadata['scan_id'])
        merged_tr.set_parent(column)
        merged_tr.set_as_parent(lines)
        pagexml_helper.check_parentage(merged_tr)
        if debug > 3:
            print(f'page_date_parser.process_handwritten_text_regions - '
                  f'adding merged tr at index {len(non_overlapping_trs)}:',
                  merged_tr.id)
            for line in merged_tr.lines:
                print('\t', line.id, line.parent.id)
        non_overlapping_trs.append(merged_tr)
    if debug > 3:
        print(f'page_date_parser.process_handwritten_text_regions - end with {len(non_overlapping_trs)} trs')
    for ti, tr in enumerate(non_overlapping_trs):
        try:
            pagexml_helper.check_parentage(tr)
        except ValueError:
            print(f"text_region idx {ti}\ttr.id: {tr.id}")
            raise
    return non_overlapping_trs


def debug_print_page_trs(page: pdm.PageXMLPage, prefix: str, debug: int = 0):
    print(f"\n{prefix}")
    print(page.stats)
    for tr in page.get_all_text_regions():
        print(tr.id, get_tr_known_types(tr), '\thas session_date', 'session_date' in tr.metadata)
        if debug > 0:
            for line in tr.lines:
                print(f"\t{line.id} line.metadata['line_class']: {line.metadata['line_class']}")


def process_handwritten_page(page: pdm.PageXMLPage, week_day_name_searcher: FuzzyPhraseSearcher = None,
                             debug: int = 0):
    """Split and/or merge columns and overlapping text regions of handwritten
    resolution pages and correct line classes for session dates, attendance
    lists, date headers and paragraphs.

    If a week_day_name_searcher is passed, line classes will be updated to date if they contain
    a weekday name.
    """
    pagexml_helper.check_parentage(page)
    page = copy_page(page)
    page.columns = process_handwritten_columns(page.columns, page)
    pagexml_helper.check_parentage(page)

    if debug > 0:
        debug_print_page_trs(page, "BEFORE page_date_parser.process_handwritten_page "
                                   "-> process_handwritten_text_regions", debug=debug)
    for col in page.columns:
        # print(f'\n{col.id}\n')
        col.text_regions = process_handwritten_text_regions(col.text_regions, col)
    pagexml_helper.check_parentage(page)

    if debug > 0:
        debug_print_page_trs(page, "BEFORE page_date_parser.process_handwritten_page "
                                   "-> split_page_column_text_regions", debug=debug)
    page = split_page_column_text_regions(page, week_day_name_searcher=week_day_name_searcher,
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


def sort_date_trs_and_lines(page: pdm.PageXMLPage, records: List[Dict[str, any]],
                            debug: int = 0) -> List[pdm.PageXMLTextRegion]:
    all_trs = []
    for record in records:
        record['lines'] = []
        record['text_region'] = None
    for tr in page.get_all_text_regions():
        tr_is_date = False
        for record in records:
            if tr.id == record['text_region_id']:
                record['text_region'] = tr
                if debug > 1:
                    print(f"\npage_date_parser.sort_date_trs_and_lines - tr: {tr.id}")
                    print(f"\ttr.type: {tr.type}")
                update_tr_type(tr, record, debug=debug)
                for line in tr.lines:
                    line.metadata['line_class'] = 'date' if record['date_type'] == 'start' else 'date_header'
                tr_is_date = True
            tr_lines = [line for line in tr.lines]
            for line in tr_lines:
                if line.id in record['line_ids']:
                    line.metadata['line_class'] = 'date' if record['date_type'] == 'start' else 'date_header'
                    record['lines'].append(line)
                    tr.lines.remove(line)
        if tr_is_date is False:
            for line in tr.lines:
                if line.metadata['line_class'] in {'date', 'date_header'}:
                    line.metadata['line_class'] = 'para_mid'
            all_trs.append(tr)

    new_trs = []
    # all_stats = combine_stats(all_trs)
    # split trs that now have a vertical gap because a date line has been removed
    for tr in all_trs:
        split_trs = column_parser.split_text_region_on_vertical_gap(tr, update_type=False, debug=0)
        new_trs.extend(split_trs)
    # new_stats = combine_stats(new_trs)
    """
    if all_stats['lines'] != page_stats['lines'] or new_stats['lines'] != all_stats['lines']:
        print(f"page_date_parser.sort_date_trs_and_lines - unequal numbers of lines")
        print(f"\tpage.stats['lines']: {page.stats['lines']}")
        print(f"\tall_stats['lines']: {all_stats['lines']}")
        print(f"\tnew_stats['lines']: {new_stats['lines']}")
        raise ValueError("unequal number of lines")
    """
    return new_trs


def derive_text_region_from_date_record(record: Dict[str, any], debug: int = 0) -> pdm.PageXMLTextRegion:
    """Generate a text_region of type date based on a date record."""
    lines = []
    metadata = None
    if record['text_region'] is not None:
        lines.extend([line for line in record['text_region'].lines])
        metadata = copy.deepcopy(record['text_region'].metadata)
    lines.extend(record['lines'])
    if len(lines) == 0:
        print(f'page_date_parser.derive_text_region_from_date_record - record: {get_record_info(record)}')
        raise IndexError(f"lines derived from date record cannot be empty.")
    coords = pdm.parse_derived_coords(lines)
    if metadata is None:
        metadata = copy.deepcopy(lines[0].metadata)
        if 'text_region_id' in metadata:
            del metadata['text_region_id']
    date_tr = pdm.PageXMLTextRegion(metadata=metadata, coords=coords, lines=lines)
    date_tr.set_as_parent(lines)
    if 'scan_id' not in metadata:
        print(f'page_date_parser.derive_text_region_from_date_record - record: {get_record_info(record)}')
        raise KeyError(f"no 'scan_id' in metadata derived from date record element(s).")
    date_tr.set_derived_id(metadata['scan_id'])
    if debug > 1:
        print("\npage_date_parser.derive_text_region_from_date_record:")
        print(f"    record: {get_record_info(record)}")
        print(f"    date_tr: {date_tr.id}")
        for line in date_tr.lines:
            print(f"\tline {line.id} has parent {line.parent.id}")
    update_tr_type(date_tr, record, debug=debug)
    date_tr.metadata['session_start'] = True
    date_tr.metadata['session_date'] = record['date']
    date_tr.metadata['second_session'] = record['second_session']
    if debug > 1:
        print(f'\npage_date_parser.derive_text_region_from_date_record - date_tr: {date_tr.id}')
        print(f"\tmetadata['session_date']: {date_tr.metadata['session_date']}")
    return date_tr


def sort_trs_by_type(trs: List[pdm.PageXMLTextRegion], debug: int = 0) -> Dict[str, List[pdm.PageXMLTextRegion]]:
    """Sort a list of text regions into a dictionary with a list of text regions per type.

    Types should be marginalia, date, attendance, resolution"""
    trs_by_type = defaultdict(list)
    for tr in trs:
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
            raise TypeError(f"tr {tr.id} has no known type")
        elif len(tr_known_types) > 1:
            print(f"page_date_parser.sort_trs_by_type - tr {tr.id} has multiple known types:")
            print(f"    known_types: {KNOWN_TYPES}")
            print(f"    tr.type: {tr.type}")
            raise TypeError(f"tr {tr.id} has multiple known types")
        for tr_type in KNOWN_TYPES:
            if tr.has_type(tr_type):
                trs_by_type[tr_type].append(tr)
    total_by_type = sum([len(trs_by_type[tr_type]) for tr_type in trs_by_type])
    if total_by_type != len(trs):
        print("page_date_parser.sort_trs_by_type:")
        print(f"    number of initial trs: {len(trs)}")
        print(f"    number of trs by type: {total_by_type}")
        for tr_type in trs_by_type:
            for tr in trs_by_type[tr_type]:
                print(f"\t{tr_type}\t{tr.id}")
        raise KeyError
    return trs_by_type


def update_page_with_date_info(page: pdm.PageXMLPage, records: List[Dict[str, any]],
                               debug: int = 0) -> pdm.PageXMLPage:
    # update lines of date regions and lines to type 'date'
    # update text regions to type date and main if they are a session start
    # update text regions to type date_header and header if they are a session start
    orig_stats = page.stats
    page = copy_page(page)
    if debug > 0:
        debug_print_page_trs(page, "BEFORE page_date_parser.update_page_with_date_info - "
                                   "split_text_region_on_vertical_gap", debug=debug)
    new_trs = sort_date_trs_and_lines(page, records, debug=debug)
    if debug > 0:
        debug_print_page_trs(page, "BEFORE page_date_parser.update_page_with_date_info - "
                                   "split_text_region_on_vertical_gap", debug=debug)
    # merge date lines into new text region
    for record in records:
        date_tr = derive_text_region_from_date_record(record, debug=debug)
        # print(f'NEW DATE_TR: {date_tr.id} with stats {date_tr.stats}')
        new_trs.append(date_tr)
    trs_by_type = sort_trs_by_type(new_trs)
    # for tr_type in trs_by_type:
    #     print(tr_type, [tr.id for tr in trs_by_type[tr_type]])
    cols = []
    metadata = copy.deepcopy(page.columns[0].metadata)
    for tr_type in trs_by_type:
        coords = pdm.parse_derived_coords(trs_by_type[tr_type])
        col = pdm.PageXMLColumn(metadata=metadata, coords=coords, text_regions=trs_by_type[tr_type])
        if debug > 0:
            print(f"page_date_parser.update_page_with_date_info - tr_type: {tr_type}")
            print(f"    coords: {coords.box}")
            print(f"    col.stats: {col.stats}")
            for tr in trs_by_type[tr_type]:
                print(f"\ttr: {tr.id} {tr.type}")
                # print(f"\ttr: {tr.id} {get_tr_known_types(tr)}")
            print('\n')
        col.set_derived_id(metadata['scan_id'])
        cols.append(col)
    new_page = pdm.PageXMLPage(doc_id=page.id, metadata=copy.deepcopy(page.metadata),
                               doc_type=copy.deepcopy(page.type), coords=copy.deepcopy(page.coords),
                               columns=cols)

    if debug > 1:
        debug_print_page_trs(page, "BEFORE page_date_parser.update_page_with_date_info - "
                                   "process_handwritten_page", debug=debug)
    # split and sort columns and text regions
    new_page = process_handwritten_page(new_page, debug=debug)
    if debug > 1:
        print("AFTER page_date_parser.process_handwritten_page")
        print(page.stats)
    for tr in new_page.get_all_text_regions():
        if 'session_date' in tr.metadata and tr.has_type('date') is False:
            del tr.metadata['session_start']
            del tr.metadata['session_date']
            del tr.metadata['second_session']
        if debug > 1:
            print(tr.id, get_tr_known_types(tr), 'session_date' in tr.metadata)

    new_stats = new_page.stats
    for field in ['lines', 'words']:
        if orig_stats[field] != new_stats[field]:
            print(f"page_date_parser.update_page_with_date_info - unequal {field} stats:")
            print(f"\toriginal page stats: {orig_stats}")
            print(f"\tupdated page stats: {new_stats}")
            raise ValueError(f"unequal number of {field} in original page ({orig_stats[field]} and"
                             f"updated page ({new_stats[field]}.")
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
    date_line_structure = get_session_date_line_structure(session_date_lines, date_token_cat,
                                                          inv_meta['inventory_id'], debug=debug)
    if debug > 0:
        print("page_date_parser.make_inventory_date_name_mapper - date_line_structure:")
        print(date_line_structure)
    try:
        date_mapper = DateNameMapper(inv_meta, date_line_structure)
    except Exception:
        print(f"Error creating DateNameMapper for inventory {inv_meta['inventory_num']}")
        print(f"with date_line_structure:", date_line_structure)
        print(f"with session_date_lines:", [line.text for line in session_date_lines])
        raise
    return date_mapper


def process_handwritten_pages(inv_id: str, pages: List[pdm.PageXMLPage],
                              filter_date_starts: bool = True, date_tr_type_map: Dict[str, str] = None,
                              ignorecase: bool = True, debug: int = 0):
    date_mapper = make_inventory_date_name_mapper(inv_id, pages, filter_date_starts=filter_date_starts,
                                                  date_tr_type_map=date_tr_type_map, debug=debug)
    config = {'ngram_size': 3, 'skip_size': 1, 'ignorecase': ignorecase, 'levenshtein_threshold': 0.8}
    week_day_name_searcher = make_week_day_name_searcher(date_mapper, config)
    new_pages = [process_handwritten_page(page, week_day_name_searcher=week_day_name_searcher,
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

    pages = process_handwritten_pages(inv_id, pages, date_tr_type_map=date_tr_type_map,
                                      ignorecase=ignorecase, debug=0)
    date_trs[inv_num] = get_header_dates(pages)
    print(f"inv {inv_num}  step 1: {len(date_trs[inv_num])}")

    date_tr_type_map = classify_page_date_regions(pages, date_region_classifier)

    date_mapper = get_inventory_date_mapper(inv_meta, pages,
                                            date_tr_type_map=date_tr_type_map,
                                            ignorecase=ignorecase, debug=0)

    week_day_name_searcher = make_week_day_name_searcher(date_mapper, config)
    pages = [process_handwritten_page(page, week_day_name_searcher=week_day_name_searcher,
                                      debug=0) for page in pages]

    print(f"inv {inv_num}  step 2: {len(date_trs[inv_num])}")
    return pages


def get_inventory_date_mapper(inv_metadata: Dict[str, any], pages: List[pdm.PageXMLPage],
                              filter_date_starts: bool = True, date_tr_type_map: Dict[str, str] = None,
                              ignorecase: bool = True, debug: int = 0):
    date_token_cat = get_date_token_cat(inv_num=inv_metadata['inventory_num'], ignorecase=ignorecase)
    session_date_lines = get_session_date_lines_from_pages(pages, filter_date_starts=filter_date_starts,
                                                           date_tr_type_map=date_tr_type_map, debug=debug)
    if len(session_date_lines) == 0:
        print(f"WARNING - No session date lines found for "
              f"inventory {inv_metadata['inventory_num']} with {len(pages)} pages")
        return None
    date_line_structure = get_session_date_line_structure(session_date_lines,
                                                          date_token_cat, inv_metadata['inventory_id'])
    """
    if 'week_day_name' not in [element[0] for element in date_line_structure]:
        print('WARNING - missing week_day_name in date_line_structure for inventory', inv_metadata['inventory_num'])
        return None
    """

    return DateNameMapper(inv_metadata, date_line_structure)