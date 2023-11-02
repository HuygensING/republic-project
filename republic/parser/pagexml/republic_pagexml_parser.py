from typing import Dict, List, Union

import pagexml
import pagexml.parser as pagexml_parser
import pagexml.model.physical_document_model as pdm
import pagexml.helper.pagexml_helper as pagexml_helper
import pagexml.analysis.layout_stats as layout_helper

import republic.parser.republic_file_parser as file_parser
# import republic.parser.pagexml.generic_pagexml_parser as pagexml_parser
from republic.parser.pagexml.republic_page_parser import split_scan_pages
from republic.parser.pagexml.republic_page_parser import derive_pagexml_page_iiif_url
from republic.parser.pagexml.republic_page_parser import split_column_regions
from republic.parser.pagexml.republic_column_parser import is_full_text_column
from republic.parser.pagexml.republic_column_parser import is_text_column
from republic.parser.pagexml.republic_column_parser import make_derived_column
# import republic.model.physical_document_model as pdm
# import republic.helper.pagexml_helper as pagexml_helper


def parse_republic_pagexml_file(pagexml_file: str) -> pdm.PageXMLScan:
    try:
        scan_doc = pagexml_parser.parse_pagexml_file(pagexml_file)
        metadata = file_parser.get_republic_scan_metadata(pagexml_file)
        for field in metadata:
            scan_doc.metadata[field] = metadata[field]
        if 'coords' not in scan_doc:
            scan_doc.coords = pdm.parse_derived_coords(scan_doc.text_regions)
        return scan_doc
    except (AssertionError, KeyError, TypeError, ValueError):
        print(f"Error parsing file {pagexml_file}")
        raise


def set_scan_type(scan: pdm.PageXMLDoc, inv_metadata: Dict[str, any] = None) -> None:
    inv_num = scan.metadata["inventory_num"]
    if 62 <= inv_num <= 456:
        scan.metadata["resolution_type"] = "ordinaris"
        scan.metadata["text_type"] = "handwritten"
        scan.metadata["normal_odd_end"] = 5500
        scan.metadata["normal_even_end"] = 2800
    elif 3096 <= inv_num <= 3348:
        scan.metadata["resolution_type"] = "ordinaris"
        scan.metadata["text_type"] = "handwritten"
        scan.metadata["normal_odd_end"] = 5500
        scan.metadata["normal_even_end"] = 2800
    elif 3760 <= inv_num <= 3864:
        scan.metadata["resolution_type"] = "ordinaris"
        scan.metadata["text_type"] = "printed"
        scan.metadata["normal_odd_end"] = 4900
        scan.metadata["normal_even_end"] = 2500
    elif 3865 <= inv_num <= 3868:
        scan.metadata["resolution_type"] = "ordinaris"
        scan.metadata["text_type"] = "handwritten"
        scan.metadata["normal_odd_end"] = 5500
        scan.metadata["normal_even_end"] = 2800
    elif 4542 <= inv_num <= 4797:
        scan.metadata["resolution_type"] = "secreet"
        scan.metadata["text_type"] = "handwritten"
        scan.metadata["normal_odd_end"] = 5500
        scan.metadata["normal_even_end"] = 2800
    elif 4806 <= inv_num <= 4861:
        scan.metadata["resolution_type"] = "speciaal"
        scan.metadata["text_type"] = "handwritten"
        scan.metadata["normal_odd_end"] = 5500
        scan.metadata["normal_even_end"] = 2800
    else:
        raise ValueError(f'Unknown REPUBLIC inventory number: {inv_num}')
    if inv_metadata and 'scan_width_stats' in inv_metadata:
        inv_scan_width = inv_metadata['scan_width_stats']['scan_width_median']
        scan.metadata["normal_odd_end"] = inv_scan_width
        scan.metadata["normal_even_end"] = inv_scan_width / 2 + 100
    if scan.coords.right == 0:
        scan.metadata['scan_type'] = ['empty_scan']
    elif scan.coords.right <= scan.metadata["normal_even_end"]:
        scan.metadata['scan_type'] = ['single_page']
    elif scan.coords.right <= scan.metadata["normal_odd_end"]:
        scan.metadata['scan_type'] = ['double_page']
    else:
        scan.metadata['scan_type'] = ['special_page']


def get_scan_pagexml(pagexml_file: str,
                     pagexml_data: Union[str, None] = None,
                     inv_metadata: Dict[str, any] = None,
                     debug: int = 0) -> pdm.PageXMLScan:
    try:
        scan_doc = pagexml_parser.parse_pagexml_file(pagexml_file, pagexml_data=pagexml_data)
    except (AssertionError, KeyError, TypeError):
        print('Error parsing file', pagexml_file)
        raise
    if not scan_doc.coords and scan_doc.text_regions:
        # add scan coordinates if they're not in the XML
        scan_doc.coords = pdm.parse_derived_coords(scan_doc.text_regions)
    for text_region in scan_doc.text_regions:
        if "text_type" in scan_doc.metadata \
                and scan_doc.metadata["text_type"] == "handwritten" \
                and text_region.has_type('date') \
                and len(' '.join([line.text for line in text_region.lines])) > 15:
            text_region.add_type(['main'])
        elif text_region.types.intersection({'date', 'page-number'}):
            text_region.add_type(['header', 'extra'])
        elif text_region.types.intersection({'catch-word', 'signature-mark'}):
            text_region.add_type(['footer', 'extra'])
        elif text_region.types.intersection({'separator'}):
            text_region.add_type(['extra'])
        elif text_region.types.intersection({'index', 'respect', 'resolution'}):
            text_region.add_type(['main'])
    metadata = file_parser.get_republic_scan_metadata(pagexml_file)
    scan_doc.id = metadata['id']
    for field in metadata:
        scan_doc.metadata[field] = metadata[field]
    set_scan_type(scan_doc, inv_metadata=inv_metadata)
    set_document_children_derived_ids(scan_doc, scan_doc.id)
    pdm.set_parentage(scan_doc)
    # print('get_scan_pagexml - setting scan_id as metadata')
    scan_doc.set_scan_id_as_metadata()
    # print('get_scan_pagexml - setting line height stats')
    set_line_heights(scan_doc, debug=debug)
    return scan_doc


def set_line_heights(scan: pdm.PageXMLScan, debug: int = 0):
    if debug > 0:
        print('set_line_heights - scan.id:', scan.id)
    for line in scan.get_lines():
        line_height_stats = layout_helper.get_line_height_stats(line, debug=debug)
        if debug > 0:
            print('set_line_heights - line_height_stats:', line_height_stats)
        if line_height_stats is None:
            return None
        if line.xheight is None:
            line.xheight = line_height_stats['mean']
        line.metadata['height'] = line_height_stats


def swap_reading_order_ids(doc: pdm.PageXMLDoc, text_region: pdm.PageXMLTextRegion,
                           old_id: str) -> None:
    doc.reading_order_number[text_region.id] = doc.reading_order_number[old_id]
    del doc.reading_order_number[old_id]
    doc.reading_order[doc.reading_order_number[text_region.id]] = text_region.id


def set_document_children_derived_ids(doc: pdm.PageXMLDoc, scan_id: str):
    pdm.set_parentage(doc)
    doc_text_regions: List[pdm.PageXMLTextRegion] = []
    if hasattr(doc, 'text_regions'):
        doc_text_regions += doc.text_regions
    if hasattr(doc, 'columns'):
        doc_text_regions += doc.columns
    if hasattr(doc, 'extra'):
        doc_text_regions += doc.extra
    for text_region in doc_text_regions:
        if text_region.id is None:
            text_region.set_derived_id(scan_id)
        if 'scan_id' not in text_region.metadata:
            text_region.metadata['scan_id'] = scan_id
        old_id = text_region.id
        text_region.set_derived_id(scan_id)
        if doc.reading_order and old_id in doc.reading_order_number:
            if old_id == text_region.id:
                continue
            swap_reading_order_ids(doc, text_region, old_id)
        if text_region.has_type('column'):
            id_field = 'column_id'
        elif text_region.has_type('header'):
            id_field = 'header_id'
        elif text_region.has_type('footer'):
            id_field = 'footer_id'
        elif doc.has_type('page'):
            id_field = 'extra_id'
        else:
            id_field = 'text_region_id'
        id_value = text_region.id
        if hasattr(text_region, 'text_regions'):
            for inner_region in text_region.text_regions:
                if inner_region.id is None:
                    inner_region.set_derived_id(scan_id)
                if 'scan_id' not in inner_region.metadata:
                    inner_region.metadata['scan_id'] = scan_id
                inner_region.metadata[id_field] = id_value
                inner_region.set_derived_id(scan_id)
                for line in inner_region.lines:
                    if line.id is None:
                        line.set_derived_id(scan_id)
                    line.metadata[id_field] = id_value
                    if 'scan_id' in text_region.metadata:
                        line.metadata['scan_id'] = text_region.metadata['scan_id']
                    if 'page_id' in text_region.metadata:
                        line.metadata['page_id'] = text_region.metadata['page_id']
                    line.set_derived_id(scan_id)
        if hasattr(text_region, 'lines'):
            for line in text_region.lines:
                if line.id is None:
                    line.set_derived_id(scan_id)
                line.metadata[id_field] = id_value
                if 'scan_id' in text_region.metadata:
                    line.metadata['scan_id'] = text_region.metadata['scan_id']
                if 'page_id' in text_region.metadata:
                    line.metadata['page_id'] = text_region.metadata['page_id']
                line.set_derived_id(scan_id)


def split_pagexml_scan(scan_doc: pdm.PageXMLScan, page_type_index: Dict[int, any],
                       debug: int = 0) -> List[pdm.PageXMLPage]:
    split_columns = True
    has_wide_main = False
    # print("SCAN TYPE:", scan_doc.type)
    for text_region in scan_doc.text_regions:
        if text_region.has_type('main') and text_region.coords.width > 1100:
            if debug > 0:
                print('split_pagexml_scan - WIDE TEXT REGION:', text_region.id)
            has_wide_main = True
        if text_region.has_type('main'):
            split_columns = False
    if has_wide_main:
        split_columns = True
    pages = split_scan_pages(scan_doc, page_type_index, debug=debug)
    if debug > 0:
        print('split_pagexml_scan - trs per page\n')
        for page in pages:
            print(page.id, page.type)
            for tr in page.columns + page.extra + page.text_regions:
                print(f"{tr.coords.x: >4}-{tr.coords.y: <4}\t{tr.coords.w}\t{tr.type}")
        print('\n')
    if split_columns:
        if debug > 0:
            print('split_pagexml_scan - Splitting page columns into narrower sub columns')
        pages = [split_column_regions(page_doc, debug=debug) for page_doc in pages]
    else:
        for page in pages:
            for text_region in page.text_regions:
                if text_region.has_type('main') and text_region.has_type('extra'):
                    text_region.remove_type('extra')
                if not text_region.type or not text_region.has_type('main') or text_region.has_type('extra'):
                    text_region.metadata['iiif_url'] = derive_pagexml_page_iiif_url(page.metadata['jpg_url'],
                                                                                    text_region.coords)
                    page.add_child(text_region, as_extra=True)
                    if debug > 0:
                        print('split_pagexml_scan - adding tr as extra:', text_region.id)
                else:
                    # turn the text region into a column
                    column = pdm.PageXMLColumn(metadata=text_region.metadata, coords=text_region.coords,
                                               text_regions=text_region.text_regions,
                                               lines=text_region.lines)
                    column.set_derived_id(scan_doc.id)
                    column.metadata['iiif_url'] = derive_pagexml_page_iiif_url(page.metadata['jpg_url'],
                                                                               column.coords)
                    if debug > 0:
                        print('split_pagexml_scan - adding tr as column:', text_region.id)
                    page.add_child(column)
            page.text_regions = []
    for page in pages:
        for text_region in page.columns + page.extra:
            text_region.set_derived_id(scan_doc.id)
            if debug > 0:
                print('split_pagexml_scan - setting derived ID:', text_region.id, 'with parent', scan_doc.id)
            if text_region.has_type('column'):
                id_field = 'column_id'
            elif text_region.has_type('header'):
                id_field = 'header_id'
            elif text_region.has_type('footer'):
                id_field = 'footer_id'
            else:
                id_field = 'extra_id'
            id_value = text_region.id
            for inner_region in text_region.text_regions:
                inner_region.metadata[id_field] = id_value
                inner_region.set_derived_id(scan_doc.id)
                inner_region.metadata['iiif_url'] = derive_pagexml_page_iiif_url(page.metadata['jpg_url'],
                                                                                 inner_region.coords)
                for line in inner_region.lines:
                    line.metadata[id_field] = id_value
                    line.metadata['scan_id'] = text_region.metadata['scan_id']
                    line.metadata['page_id'] = text_region.metadata['page_id']
                    line.set_derived_id(scan_doc.id)
            for line in text_region.lines:
                line.metadata[id_field] = id_value
                line.metadata['scan_id'] = text_region.metadata['scan_id']
                line.metadata['page_id'] = text_region.metadata['page_id']
                line.set_derived_id(scan_doc.id)
    return pages


def has_overlapping_columns(page: pdm.PageXMLPage) -> bool:
    """Determine whether a page has columns that
    mostly overlap with each other"""
    for ci, curr_column in enumerate(page.columns):
        if ci == len(page.columns) - 1:
            break
        for next_column in page.columns[ci + 1:]:
            if pagexml_helper.elements_overlap(curr_column, next_column, threshold=0.8):
                print('Overlapping columns!')
                print('\t', curr_column.coords.box)
                print('\t', next_column.coords.box)
    return False


def has_text_columns(page: pdm.PageXMLPage, num_page_cols: int = 2) -> bool:
    for column in page.columns:
        if is_full_text_column(column, num_page_cols=num_page_cols):
            return True
    return False


def is_title_page(page: pdm.PageXMLPage) -> bool:
    """Check whether a page is a Republic title page."""
    # title pages are always on the right side of the scan
    # and have an uneven page number
    if page.metadata['page_num'] % 2 == 0:
        return False
    num_title_lines = 0
    for line in page.get_lines():
        if line.coords.left < 3500 and line.coords.right > 3600:
            if line.coords.width / len(line.text) > 30:
                num_title_lines += 1
    return num_title_lines > 2


def parse_title_page_columns(page: pdm.PageXMLPage) -> pdm.PageXMLPage:
    extra_columns = page.extra
    text_columns = []
    for column in page.columns:
        if not is_text_column(column):
            extra_columns.append(column)
            continue
        if column.stats['lines'] < 10:
            extra_columns.append(column)
            continue
        if column.coords.width < 1000:
            text_columns.append(column)
            continue
        lines = sorted(column.get_lines(), key=lambda x_line: x_line.coords.y)
        last_title_line_index = -1
        for li, line in enumerate(lines):
            if line.coords.left < 3400 and line.coords.right > 3600:
                last_title_line_index = li
        title_lines = lines[:last_title_line_index + 1]
        if len(title_lines) > 0:
            title_column = make_derived_column(title_lines, column.metadata, page.id)
            extra_columns.append(title_column)
        body_lines = lines[last_title_line_index + 1:]
        left_col_lines, right_col_lines = [], []
        for line in body_lines:
            if line.coords.right < 3600:
                left_col_lines.append(line)
            elif line.coords.left > 3400 and line.coords.right >= 3600:
                right_col_lines.append(line)
            else:
                print(line.coords.box)
                print(line.text)
                raise TypeError('cannot select appropriate column')
        if len(left_col_lines) > 0:
            left_column = make_derived_column(left_col_lines, column.metadata, page.metadata['scan_id'])
            text_columns.append(left_column)
        if len(right_col_lines) > 0:
            right_column = make_derived_column(right_col_lines, column.metadata, page.metadata['scan_id'])
            text_columns.append(right_column)
    new_page_coords = pdm.parse_derived_coords(extra_columns + text_columns)
    new_page = pdm.PageXMLPage(metadata=page.metadata, coords=new_page_coords, columns=text_columns,
                               text_regions=page.text_regions, extra=extra_columns)
    new_page.set_derived_id(page.metadata['scan_id'])
    return new_page
