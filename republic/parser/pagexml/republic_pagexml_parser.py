from typing import List, Union, Dict
import numpy as np
import copy

from republic.helper.metadata_helper import make_iiif_region_url
import republic.parser.republic_file_parser as file_parser
import republic.parser.pagexml.generic_pagexml_parser as pagexml_parser
from republic.parser.pagexml.generic_pagexml_parser import parse_derived_coords


def parse_republic_pagexml_file(pagexml_file: str) -> dict:
    try:
        scan_json = file_parser.read_pagexml_file(pagexml_file)
        scan_doc = pagexml_parser.parse_pagexml(scan_json)
        metadata = file_parser.get_republic_scan_metadata(pagexml_file)
        for field in metadata:
            scan_doc['metadata'][field] = metadata[field]
        if 'coords' not in scan_doc:
            scan_doc['coords'] = parse_derived_coords(scan_doc['textregions'])
        return scan_doc
    except (AssertionError, KeyError, TypeError):
        print(f"Error parsing file {pagexml_file}")
        raise


def get_scan_pagexml(pagexml_file: str, inventory_config: dict, pagexml_data: Union[str, None] = None) -> dict:
    #print('Parsing file', pagexml_file)
    scan_json = file_parser.read_pagexml_file(pagexml_file, pagexml_data=pagexml_data)
    try:
        scan_doc = pagexml_parser.parse_pagexml(scan_json)
    except (AssertionError, KeyError, TypeError):
        print('Error parsing file', pagexml_file)
        raise
    if 'coords' not in scan_doc:
        # add scan coordinates if they're not in the XML
        textregions = scan_doc['textregions'] if 'textregions' in scan_doc else []
        scan_doc['coords'] = parse_derived_coords(textregions)
    metadata = file_parser.get_republic_scan_metadata(pagexml_file)
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
    return item['coords']['left'] > 2400
    # return item['coords']['right'] < 4800 and item['coords']['left'] > 2400


def is_extra_side(item: dict) -> bool:
    return item['coords']['right'] > 4800 and item['coords']['left'] > 4700


def initialize_pagexml_page(scan_doc: dict, side: str) -> dict:
    """Initialize a pagexml page type document based on the scan metadata."""
    page_doc = {
        'metadata': copy.copy(scan_doc['metadata']), 'textregions': [], 'coords': None
    }
    page_doc['metadata']['doc_type'] = 'page'
    page_doc['metadata']['page_side'] = side
    if side == 'odd':
        page_num = scan_doc['metadata']['scan_num'] * 2 - 1
        doc_id = f"{scan_doc['metadata']['id']}-page-{page_num}"
    elif side == 'even':
        page_num = scan_doc['metadata']['scan_num'] * 2 - 2
        doc_id = f"{scan_doc['metadata']['id']}-page-{page_num}"
    else:
        page_num = scan_doc['metadata']['scan_num'] * 2 - 2
        doc_id = f"{scan_doc['metadata']['id']}-page-{page_num}-extra"
    page_doc['metadata']['page_num'] = page_num
    page_doc['metadata']['id'] = doc_id
    return page_doc


def split_scan_pages(scan_doc: dict) -> List[dict]:
    pages = []
    if not 'textregions' in scan_doc:
        return pages
    page_odd = initialize_pagexml_page(scan_doc, 'odd')
    page_even = initialize_pagexml_page(scan_doc, 'even')
    # page_extra = initialize_pagexml_page(scan_doc, 'extra')
    for textregion in scan_doc['textregions']:
        if 'lines' in textregion:
            even_lines = [line for line in textregion['lines'] if is_even_side(line)]
            odd_lines = [line for line in textregion['lines'] if is_odd_side(line)]
            # extra_lines = [line for line in textregion['lines'] if is_extra_side(line)]
            if len(even_lines) > 0:
                page_even['textregions'] += [{'lines': even_lines, 'coords': parse_derived_coords(even_lines)}]
            if len(odd_lines) > 0:
                page_odd['textregions'] += [{'lines': odd_lines, 'coords': parse_derived_coords(odd_lines)}]
            # if len(extra_lines) > 0:
            #    page_extra['textregions'] += [{'lines': extra_lines, 'coords': parse_derived_coords(extra_lines)}]
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
            # if len(extra_textregions) > 0:
            #     page_extra['textregions'] += [{'textregions': extra_textregions,
            #                                    'coords': parse_derived_coords(extra_textregions)}]
    for page_doc in [page_even, page_odd]: # , page_extra]:
        if len(page_doc['textregions']) > 0:
            page_doc['coords'] = parse_derived_coords(page_doc['textregions'])
            page_doc['metadata']['iiif_url'] = derive_pagexml_page_iiif_url(page_doc['metadata']['jpg_url'],
                                                                            page_doc['coords'])
            pages += [page_doc]
    return pages


def derive_pagexml_page_iiif_url(jpg_url: str, coords: dict) -> str:
    region = {
        'left': coords['left'] - 100,
        'top': coords['top'] - 100,
        'width': coords['width'] + 200,
        'height': coords['height'] + 200,
    }
    return make_iiif_region_url(jpg_url, region)


def coords_overlap(item1: dict, item2: dict) -> int:
    coords1, coords2 = item1['coords'], item2['coords']
    left = coords1['left'] if coords1['left'] > coords2['left'] else coords2['left']
    right = coords1['right'] if coords1['right'] < coords2['right'] else coords2['right']
    # overlap must be positive, else there is no overlap
    return right - left if right - left > 0 else 0


def get_median_normal_line_score(scores):
    median_score = np.median(scores)
    normal_scores = [score for score in scores if abs(score - median_score) < 50]
    return np.median(normal_scores)


def set_line_alignment(column: dict):
    lines = [line for textregion in column["textregions"] for line in textregion["lines"]]
    lefts = [line["coords"]["left"] for line in lines]
    rights = [line["coords"]["right"] for line in lines]
    widths = [line["coords"]["width"] for line in lines]
    lengths = [len(line["text"]) for line in lines]
    column["metadata"]["median_normal_left"] = get_median_normal_line_score(lefts)
    column["metadata"]["median_normal_right"] = get_median_normal_line_score(rights)
    column["metadata"]["median_normal_width"] = get_median_normal_line_score(widths)
    column["metadata"]["median_normal_length"] = get_median_normal_line_score(lengths)
    for ti, tr in enumerate(column["textregions"]):
        for li, line in enumerate(tr["lines"]):
            line["metadata"] = {"id": column["metadata"]["id"] + f"-tr-{ti}-line-{li}"}
            if line["coords"]["left"] > column["metadata"]["median_normal_left"] + 50:
                line["metadata"]["left_alignment"] = "indent"
            else:
                line["metadata"]["left_alignment"] = "column"
            if line["coords"]["right"] < column["metadata"]["median_normal_right"] - 50:
                line["metadata"]["right_alignment"] = "indent"
            else:
                line["metadata"]["right_alignment"] = "column"


def split_column_regions(page_doc: dict) -> dict:
    header = {'textregions': []}
    columns = []
    textregions = []
    for textregion in page_doc['textregions']:
        textregions += [textregion] if 'lines' in textregion else textregion['textregions']
    textregions.sort(key=lambda x: x['coords']['top'])
    for textregion in textregions:
        if 'lines' in textregion and textregion['coords']['width'] > 1200:
            # Wide textregions are part of the header
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
    for ci, column in enumerate(columns):
        column['textregions'].sort(key=lambda x: x['coords']['top'])
        column["metadata"] = {"type": "column", "id": page_doc["metadata"]["id"] + f"-column-{ci}"}
        col_stats = get_pagexml_doc_num_words(column)
        set_line_alignment(column)
        column['metadata']['num_lines'] = col_stats['num_lines']
        column['metadata']['num_words'] = col_stats['num_words']
        column['metadata']['iiif_url'] = derive_pagexml_page_iiif_url(page_doc['metadata']['jpg_url'], column['coords'])
    header['metadata'] = {'type': 'header'}
    header['coords'] = parse_derived_coords(header['textregions'])
    col_stats = get_pagexml_doc_num_words(header)
    header['metadata']['num_lines'] = col_stats['num_lines']
    header['metadata']['num_words'] = col_stats['num_words']
    header['metadata']['iiif_url'] = derive_pagexml_page_iiif_url(page_doc['metadata']['jpg_url'], header['coords'])
    column_doc = {
        'metadata': copy.copy(page_doc['metadata']),
        'header': header,
        'columns': columns,
        'coords': parse_derived_coords(header['textregions'] + columns),
    }
    return column_doc


def get_pagexml_doc_num_words(pagexml_doc: dict) -> Dict[str, int]:
    num_lines = 0
    num_words = 0
    doc_type = pagexml_doc['metadata']['type']
    if doc_type in ['column', 'header'] and 'textregions' in pagexml_doc:
        for textregion in pagexml_doc['textregions']:
            if 'lines' in textregion:
                text_lines = [line for line in textregion['lines'] if 'text' in line and line['text']]
                num_lines += len(text_lines)
                num_words += len([word for line in text_lines for word in line['text'].split(' ')])
    if pagexml_doc['metadata']['type'] == 'page' and 'columns' in pagexml_doc:
        for column_doc in pagexml_doc['columns']:
            col_stats = get_pagexml_doc_num_words(column_doc)
            num_lines += col_stats['num_lines']
            num_words += col_stats['num_words']
        if 'header' in pagexml_doc and 'textregions' in pagexml_doc['header']:
            header_stats = get_pagexml_doc_num_words(pagexml_doc['header'])
            num_lines += header_stats['num_lines']
            num_words += header_stats['num_words']
    return {'num_lines': num_lines, 'num_words': num_words}


def split_pagexml_scan(scan_doc: dict) -> List[dict]:
    pages = split_scan_pages(scan_doc)
    columnised_pages = [split_column_regions(page_doc) for page_doc in pages]
    for page_doc in columnised_pages:
        page_stats = get_pagexml_doc_num_words(page_doc)
        page_doc['metadata']['num_columns'] = len(page_doc['columns']) if 'columns' in page_doc else 0
        page_doc['metadata']['num_lines'] = page_stats['num_lines']
        page_doc['metadata']['num_words'] = page_stats['num_words']
    return columnised_pages
