from typing import List, Union
import copy

import republic.parser.republic_file_parser as file_parser
import republic.parser.pagexml.generic_pagexml_parser as pagexml_parser
from republic.parser.pagexml.generic_pagexml_parser import parse_derived_coords


def parse_republic_pagexml_file(pagexml_file: str, inventory_config: dict) -> dict:
    try:
        scan_json = file_parser.read_pagexml_file(pagexml_file)
        scan_doc = pagexml_parser.parse_pagexml(scan_json)
        metadata = file_parser.get_republic_scan_metadata(pagexml_file, inventory_config)
        for field in metadata:
            scan_doc['metadata'][field] = metadata[field]
        if 'coords' not in scan_doc:
            scan_doc['coords'] = parse_derived_coords(scan_doc['textregions'])
        return scan_doc
    except (AssertionError, KeyError, TypeError):
        print(f"Error parsing file {pagexml_file}")
        raise


def get_scan_pagexml(pagexml_file: str, pagexml_data: Union[str, None] = None, config: dict = {}) -> dict:
    print('Parsing file', pagexml_file)
    scan_json = file_parser.read_pagexml_file(pagexml_file, pagexml_data=pagexml_data)
    try:
        scan_doc = pagexml_parser.parse_pagexml(scan_json)
    except (AssertionError, KeyError, TypeError):
        print('Error parsing file', pagexml_file)
        raise
    if 'coords' not in scan_doc: # add scan coordinates if they're not in the XML
        textregions = scan_doc['textregions'] if 'textregions' in scan_doc else []
        scan_doc['coords'] = parse_derived_coords(textregions)
    metadata = file_parser.get_republic_scan_metadata(pagexml_file, config)
    for field in metadata:
        scan_doc['metadata'][field] = metadata[field]
    if scan_doc['coords']['right'] == 0:
        scan_doc['metadata']['scan_type'] = ['empty_scan']
    elif scan_doc['coords']['right'] < 2500:
        scan_doc['metadata']['scan_type'] = ['single_page']
    elif scan_doc['coords']['right'] < 4900:
        scan_doc['metadata']['scan_type'] = ['double_page']
    else:
        scan_doc['metadata']['scan_type'] = ['special_page']
    return scan_doc


def is_even_side(item: dict) -> bool:
    return item['coords']['right'] < 2500


def is_odd_side(item: dict) -> bool:
    return item['coords']['right'] < 4800 and item['coords']['left'] > 2400


def is_extra_side(item: dict) -> bool:
    return item['coords']['right'] > 4800 and item['coords']['left'] > 4700


def split_scan_pages(scan_doc: dict) -> List[dict]:
    pages = []
    page_odd = {'metadata': copy.copy(scan_doc['metadata']), 'textregions': [], 'coords': None}
    page_odd['metadata']['page_side'] = 'odd'
    page_odd['metadata']['page_num'] = scan_doc['metadata']['scan_num'] * 2 - 1
    page_odd['metadata']['page_id'] = '{}-page-{}'.format(scan_doc['metadata']['scan_id'],
                                                          page_odd['metadata']['page_num'])
    page_even = {'metadata': copy.copy(scan_doc['metadata']), 'textregions': [], 'coords': None}
    page_even['metadata']['page_side'] = 'even'
    page_even['metadata']['page_num'] = scan_doc['metadata']['scan_num'] * 2 - 2
    page_even['metadata']['page_id'] = '{}-page-{}'.format(scan_doc['metadata']['scan_id'],
                                                           page_even['metadata']['page_num'])
    page_extra = {'metadata': copy.copy(scan_doc['metadata']), 'textregions': [], 'coords': None}
    page_extra['metadata']['page_side'] = 'extra'
    page_extra['metadata']['page_id'] = '{}-page-extra'.format(scan_doc['metadata']['scan_id'])
    for textregion in scan_doc['textregions']:
        if 'lines' in textregion:
            even_lines = [line for line in textregion['lines'] if is_even_side(line)]
            odd_lines = [line for line in textregion['lines'] if is_odd_side(line)]
            extra_lines = [line for line in textregion['lines'] if is_extra_side(line)]
            if len(even_lines) > 0:
                page_even['textregions'] += [{'lines': even_lines, 'coords': parse_derived_coords(even_lines)}]
            if len(odd_lines) > 0:
                page_odd['textregions'] += [{'lines': odd_lines, 'coords': parse_derived_coords(odd_lines)}]
            if len(extra_lines) > 0:
                page_extra['textregions'] += [{'lines': extra_lines, 'coords': parse_derived_coords(extra_lines)}]
        if 'textregions' in textregion:
            even_textregions = [textregion for textregion in textregion['textregions'] if is_even_side(textregion)]
            odd_textregions = [textregion for textregion in textregion['textregions'] if is_odd_side(textregion)]
            extra_textregions = [textregion for textregion in textregion['textregions'] if is_extra_side(textregion)]
            if len(even_textregions) > 0:
                page_even['textregions'] += [{'textregions': even_textregions,
                                              'coords': parse_derived_coords(even_textregions)}]
            if len(odd_textregions) > 0:
                page_odd['textregions'] += [{'textregions': odd_textregions,
                                             'coords': parse_derived_coords(odd_textregions)}]
            if len(extra_textregions) > 0:
                page_extra['textregions'] += [{'textregions': extra_textregions,
                                               'coords': parse_derived_coords(extra_textregions)}]
    if len(page_even['textregions']) > 0:
        page_even['coords'] = parse_derived_coords(page_even['textregions'])
        pages += [page_even]
    if len(page_odd['textregions']) > 0:
        page_odd['coords'] = parse_derived_coords(page_odd['textregions'])
        pages += [page_odd]
    if len(page_extra['textregions']) > 0:
        page_extra['coords'] = parse_derived_coords(page_extra['textregions'])
        pages += [page_extra]
    return pages


def coords_overlap(item1: dict, item2: dict) -> int:
    coords1, coords2 = item1['coords'], item2['coords']
    left = coords1['left'] if coords1['left'] > coords2['left'] else coords2['left']
    right = coords1['right'] if coords1['right'] < coords2['right'] else coords2['right']
    return right - left if right - left > 0 else 0 # overlap must be positive, else there is no overlap


def split_column_regions(page_doc: dict) -> dict:
    header = {'textregions': []}
    columns = []
    textregions = []
    for textregion in page_doc['textregions']:
        textregions += [textregion] if 'lines' in textregion else textregion['textregions']
    textregions.sort(key=lambda x: x['coords']['top'])
    #for textregion in page_doc['textregions']:
    for textregion in textregions:
        if 'lines' in textregion and textregion['coords']['width'] > 1200:
            header['textregions'] += [textregion]
            continue
        # check if this text region overlaps with an existing column
        overlapping_column = None
        for column in columns:
            overlap = coords_overlap(column, textregion)
            #      column['coords']['left'], column['coords']['right'])
            tr_overlap_frac = overlap / textregion['coords']['width']
            cl_overlap_frac = overlap / column['coords']['width']
            if min(tr_overlap_frac, cl_overlap_frac) > 0.5 and max(tr_overlap_frac, cl_overlap_frac) > 0.75:
                overlapping_column = column
                break
        # if there is an overlapping column, add this text region
        if overlapping_column:
            overlapping_column['textregions'] += [textregion]
            overlapping_column['coords'] = parse_derived_coords(overlapping_column['textregions'])
        # if no, create a new column for this text region
        else:
            column = {'coords': parse_derived_coords([textregion]), 'textregions': [textregion]}
            columns += [column]
    for column in columns:
        if 'coords' not in column:
            print('COLUMN NO COORDS:', column)
            raise KeyError('Column has no "coords" property.')
    columns.sort(key=lambda x: x['coords']['left'])
    for column in columns:
        column['textregions'].sort(key=lambda x: x['coords']['top'])
    return {
        'metadata': page_doc['metadata'],
        'header': header,
        'columns': columns,
        'coords': parse_derived_coords(header['textregions'] + columns),
    }


def split_pagexml_scan(scan_doc: dict) -> List[dict]:
    pages = split_scan_pages(scan_doc)
    columnised_pages = [split_column_regions(page_doc) for page_doc in pages]
    return columnised_pages