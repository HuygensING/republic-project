from typing import Dict, List, Tuple, Union
import copy

from republic.helper.metadata_helper import make_iiif_region_url
import republic.model.physical_document_model as pdm
from republic.config.republic_config import base_config
from republic.parser.pagexml.republic_column_parser import split_lines_on_column_gaps
from republic.parser.pagexml.republic_column_parser import determine_column_type
import republic.helper.pagexml_helper as pagexml_helper


def derive_pagexml_page_iiif_url(jpg_url: str, coords: pdm.Coords) -> str:
    region = {
        'left': coords.left - 100,
        'top': coords.top - 100,
        'width': coords.width + 200,
        'height': coords.height + 200,
    }
    return make_iiif_region_url(jpg_url, region)


def split_column_regions(page_doc: pdm.PageXMLPage, config: Dict[str, any] = base_config,
                         debug: bool = False) -> pdm.PageXMLPage:
    if debug:
        print('SPLITTING PAGE INTO COLUMN REGIONS')
    column_metadata = {
        'page_id': page_doc.metadata['id'],
        'scan_id': page_doc.metadata['scan_id'],
        'type': ['column', 'pagexml_doc', 'text_region']
    }
    extra_metadata = copy.deepcopy(column_metadata)
    extra_metadata['type'] = 'header'
    columns: List[pdm.PageXMLColumn] = []
    extra_text_regions: List[pdm.PageXMLTextRegion] = []
    text_regions: List[pdm.PageXMLTextRegion] = []
    if "text_type" not in page_doc.metadata:
        pagexml_helper.set_scan_type(page_doc)
    if page_doc.metadata["text_type"] == "printed":
        max_column_width = 1200
    else:
        max_column_width = 2200
    trs = page_doc.text_regions + page_doc.columns
    for text_region in trs:
        if len(text_region.text_regions) > 0:
            text_regions += text_region.text_regions
        elif text_region.lines and text_region.coords.width > max_column_width:
            if debug:
                print(f'\tWIDE TEXT REGION {text_region.id}, SPLITTING')
            config = copy.deepcopy(config)
            config["column_gap"]["gap_pixel_freq_ratio"] = 0.5
            # print('split_column_regions - column_gap:', config['column_gap'])
            cols = split_lines_on_column_gaps(text_region, config, debug=debug)
            text_regions += cols
            for col in cols:
                col.set_parent(page_doc)
                col.set_derived_id(page_doc.id)
            if debug:
                print(f'\tAFTER SPLITTING REGION IS {len(cols)} COLUMNS')
        else:
            text_regions.append(text_region)
        # text_regions += [text_region] if text_region.lines else text_region.text_regions
    text_regions.sort(key=lambda x: x.coords.top)
    text_regions = split_merged_regions(text_regions)
    # remove the text_regions as direct descendants of page
    page_doc.text_regions = []
    for text_region in text_regions:
        if text_region.lines and text_region.coords.width > max_column_width:
            # Wide text_regions are part of the header
            text_region.main_type = 'extra'
            text_region.add_type('extra')
        if text_region.has_type('extra'):
            extra_text_regions += [text_region]
            continue
        # check if this text region overlaps with an existing column
        overlapping_column = None
        for column in columns:
            overlap = pagexml_helper.coords_overlap(column, text_region)
            tr_overlap_frac = overlap / text_region.coords.width
            cl_overlap_frac = overlap / column.coords.width
            if min(tr_overlap_frac, cl_overlap_frac) > 0.5 and max(tr_overlap_frac, cl_overlap_frac) > 0.75:
                overlapping_column = column
                break
        # if there is an overlapping column, add this text region
        if overlapping_column:
            overlapping_column.text_regions += [text_region]
            overlapping_column.coords = pdm.parse_derived_coords(overlapping_column.text_regions)
        # if no, create a new column for this text region
        else:
            column = pdm.PageXMLColumn(coords=pdm.parse_derived_coords([text_region]), metadata=column_metadata,
                                       text_regions=[text_region])
            columns += [column]
    for column in columns:
        if not column.coords:
            print('COLUMN NO COORDS:', column)
            raise KeyError('Column has no "coords" property.')
    columns.sort(key=lambda x: x.coords.left)
    for ci, column in enumerate(columns):
        column.text_regions.sort(key=lambda x: x.coords.top)
        column.metadata = column_metadata
        column.set_derived_id(column.metadata['scan_id'])
        pagexml_helper.set_line_alignment(column)
        pagexml_helper.copy_reading_order(page_doc, column)
        column.metadata['iiif_url'] = derive_pagexml_page_iiif_url(page_doc.metadata['jpg_url'], column.coords)
    if extra_text_regions:
        extra_coords = pdm.parse_derived_coords(extra_text_regions)
        extra = pdm.PageXMLTextRegion(metadata=extra_metadata, coords=extra_coords, text_regions=extra_text_regions)
        extra.main_type = 'extra'
        extra.metadata['iiif_url'] = derive_pagexml_page_iiif_url(page_doc.metadata['jpg_url'], extra.coords)
        extra.set_derived_id(extra.metadata['scan_id'])
    new_page = pdm.PageXMLPage(doc_id=page_doc.id, doc_type=page_doc.type, coords=page_doc.coords,
                               metadata=page_doc.metadata, columns=columns, extra=extra_text_regions,
                               reading_order=page_doc.reading_order)
    new_page.set_parent(page_doc.parent)
    return new_page


def get_page_split_widths(item: pdm.PhysicalStructureDoc) -> Tuple[int, int]:
    # odd_end, even_end = 4900, 2500
    scan_width = None
    # use scan width if it's available
    if 'scan_width' in item.metadata:
        scan_width = item.metadata['scan_width']
    elif item.parent and 'scan_width' in item.parent.metadata:
        scan_width = item.parent.metadata['scan_width']
    # otherwise, default to expected size
    elif 'normal_odd_end' in item.metadata:
        scan_width = item.metadata['normal_odd_end']
    elif item.parent and 'normal_odd_end' in item.parent.metadata:
        scan_width = item.parent.metadata['normal_odd_end']
    odd_end = scan_width
    if scan_width is None:
        odd_end, even_end = 0, 0
    elif "normal_odd_end" in item.metadata and scan_width > item.metadata['normal_odd_end']:
        even_end = item.metadata['normal_even_end']
    else:
        even_end = scan_width / 2 + 100
    return odd_end, even_end


def is_even_side(item: pdm.PhysicalStructureDoc) -> bool:
    odd_end, even_end = get_page_split_widths(item)
    return item.coords.left < even_end - 100 and item.coords.right < even_end


def is_odd_side(item: pdm.PhysicalStructureDoc) -> bool:
    odd_end, even_end = get_page_split_widths(item)
    return item.coords.left > even_end - 300 and item.coords.right > even_end


def is_extra_side(item: pdm.PhysicalStructureDoc) -> bool:
    odd_end, even_end = get_page_split_widths(item)
    return item.coords.right > odd_end and item.coords.left > odd_end - 200


def initialize_pagexml_page(scan_doc: pdm.PageXMLScan, side: str,
                            page_type_index: Dict[int, any]) -> pdm.PageXMLPage:
    """Initialize a pagexml page type document based on the scan metadata."""
    metadata = copy.copy(scan_doc.metadata)
    if 'doc_type' in metadata:
        del metadata['doc_type']
    metadata['type'] = 'page'
    metadata['page_side'] = side
    if side == 'odd':
        metadata['page_num'] = scan_doc.metadata['scan_num'] * 2 - 1
        metadata['id'] = f"{scan_doc.metadata['id']}-page-{metadata['page_num']}"
    elif side == 'even':
        metadata['page_num'] = scan_doc.metadata['scan_num'] * 2 - 2
        metadata['id'] = f"{scan_doc.metadata['id']}-page-{metadata['page_num']}"
    else:
        metadata['page_num'] = scan_doc.metadata['scan_num'] * 2 - 2
        metadata['id'] = f"{scan_doc.metadata['id']}-page-{metadata['page_num']}-extra"
    metadata['scan_id'] = scan_doc.metadata['id']
    page_doc = pdm.PageXMLPage(doc_id=metadata['id'], metadata=metadata, text_regions=[])
    page_doc.set_parent(scan_doc)
    if page_type_index and metadata['page_num'] in page_type_index:
        page_type = page_type_index[metadata['page_num']]
        page_doc.add_type(page_type)
    return page_doc


def combine_stats(text_regions: List[pdm.PageXMLTextRegion]) -> Dict[str, int]:
    combined_stats = {
        'words': 0,
        'lines': 0,
        'text_regions': 0,
        'columns': 0
    }
    for tr in text_regions:
        tr_stats = tr.stats
        for field in combined_stats:
            combined_stats[field] += tr_stats[field] if field in tr_stats else 0
    return combined_stats


def get_column_text_regions(scan_doc: pdm.PageXMLScan, max_col_width: int, config: Dict[str, any],
                            debug: bool = False) -> List[Union[pdm.PageXMLTextRegion, pdm.PageXMLColumn]]:
    trs = []
    for ti, tr in enumerate(scan_doc.text_regions):
        if tr.parent is None:
            print('MISSING PARENT:', tr.id)
        if tr.coords.width <= max_col_width and is_even_side(tr) or is_odd_side(tr):
            if 'main' in tr.type:
                col = pdm.PageXMLColumn(metadata=tr.metadata, coords=tr.coords,
                                        text_regions=tr.text_regions, lines=tr.lines)
                col.set_derived_id(scan_doc.id)
                col.set_parent(scan_doc)
                trs.append(col)
            else:
                trs.append(tr)
        else:
            if debug:
                if tr.coords.width > max_col_width:
                    print("SPLITTING COLUMN BECAUSE IT IS TOO WIDE", tr.id)
                else:
                    print("SPLITTING COLUMN FOR SOME OTHER REASON", tr.id)
                print(tr.stats)
            config = copy.deepcopy(config)
            config['column_gap']['gap_threshold'] = 20
            config['column_gap']['gap_pixel_freq_ratio'] = 0.5
            cols = split_lines_on_column_gaps(tr, config, debug=debug)
            if debug:
                for col in cols:
                    print("COLUMN:", col.id)
                    for line in col.lines:
                        print(f"\tLINE {line.coords.left}-{line.coords.right}\t{line.coords.y}\t{line.text}")
            trs += cols
        # tr_stats = combine_stats(trs)
        # print(ti, tr_stats)
    return trs


def assign_trs_to_odd_even_pages(scan_doc: pdm.PageXMLScan, trs: List[pdm.PageXMLTextRegion],
                                 page_type_index: Dict[int, any], config: Dict[str, any],
                                 debug: bool = False) -> List[pdm.PageXMLPage]:
    page_even = initialize_pagexml_page(scan_doc, 'even', page_type_index)
    page_odd = initialize_pagexml_page(scan_doc, 'odd', page_type_index)
    tr_id_map = {}
    undecided = []
    append_count = 0
    if debug:
        print(f'STARTING WITH {len(trs)} TRS')
    for text_region in sorted(trs, key=lambda x: x.coords.x):
        if text_region.has_type('main') and text_region.has_type('extra'):
            text_region.remove_type('extra')
        if scan_doc.metadata['inventory_num'] < 3700 or scan_doc.metadata['inventory_num'] > 4500:
            if text_region.has_type('date') and text_region.has_type('extra'):
                text_region.add_type('main')
                text_region.remove_type('extra')
        as_extra = 'extra' in text_region.type
        text_region.metadata['scan_id'] = scan_doc.id
        if text_region.metadata and 'type' in text_region.metadata:
            if debug:
                print("DECIDING EVEN/ODD SIDE", text_region.id)
            if is_even_side(text_region) or is_odd_side(text_region):
                side = 'EVEN' if is_even_side(text_region) else 'ODD'
                page = page_even if is_even_side(text_region) else page_odd
                before_stats = page.stats
                if debug:
                    print(f"\tPAGE {side} STATS BEFORE ADDING DERIVED TR:", page.stats)
                    print(f"\t{side}:", text_region.id, text_region.type)
                    print('\t\t', text_region.stats)
                page.add_child(text_region, as_extra=as_extra)
                after_stats = page.stats
                if text_region.stats['lines'] + before_stats['lines'] != after_stats['lines']:
                    print('BEFORE:', before_stats)
                    print('text_region:', text_region.stats)
                    print('AFTER:', after_stats)
                    raise ValueError('Line missing in page line count after adding text_region')
                if debug:
                    print(f"\tPAGE {side} STATS AFTER ADDING DERIVED TR:", page.stats)
                append_count += 1
            else:
                if text_region.coords is None:
                    lines = text_region.get_lines()
                    text_region.coords = pdm.parse_derived_coords(lines)
                if debug:
                    print('\tSPLITTING PAGE BOUNDARY OVERLAPPING REGION:', text_region.id, text_region.type)
                    # print(config)
                sub_trs = split_lines_on_column_gaps(text_region, config=config, debug=debug)
                if debug:
                    print('\t\tnumber of sub text regions:', len(sub_trs))
                for sub_tr in sub_trs:
                    if is_even_side(sub_tr):
                        side = 'even'
                        page = page_even
                    elif is_odd_side(sub_tr):
                        side = 'odd'
                        page = page_odd
                    else:
                        if debug:
                            print('\tUNDECIDED:', sub_tr.id, sub_tr.type)
                        undecided.append(sub_tr)
                        append_count += 1
                        continue
                    sub_tr.set_derived_id(page.id)
                    sub_tr.set_parent(page)
                    if debug:
                        print(f"PAGE {side} STATS BEFORE ADDING DERIVED TR:", page.stats)
                    page.add_child(sub_tr, as_extra=as_extra)
                    append_count += 1
                    if debug:
                        print(f"PAGE {side} STATS AFTER ADDING DERIVED TR:", page.stats)
                    if debug:
                        print(f'\tSPLIT SUB TR {side}:', sub_tr.id)
                        print('\t', sub_tr.type)
                        print('\t', sub_tr.stats)
                # undecided.append(text_region)
        elif text_region.lines:
            if debug:
                print("TEXTREGION HAS NO TYPE BUT HAS LINES:", text_region.id)
            even_lines = [line for line in text_region.lines if is_even_side(line)]
            odd_lines = [line for line in text_region.lines if is_odd_side(line)]
            if len(even_lines) == 0:
                if debug:
                    print("NO EVEN, MOVE TR TO ODD")
                page_odd.add_child(text_region, as_extra=as_extra)
            elif len(odd_lines) == 0:
                if debug:
                    print("NO ODD, MOVE TR TO EVEN")
                page_even.add_child(text_region, as_extra=as_extra)
            else:
                # The text region crosses the page boundary. Split the lines into new text regions per
                # page, and create new text regions
                if debug:
                    print("SPLIT LINES")
                odd_region = pdm.PageXMLTextRegion(lines=odd_lines, coords=pdm.parse_derived_coords(odd_lines),
                                                   metadata=text_region.metadata)
                even_region = pdm.PageXMLTextRegion(lines=even_lines, coords=pdm.parse_derived_coords(even_lines),
                                                    metadata=text_region.metadata)
                if debug:
                    print("ODD REGION", odd_region.id, odd_region.stats)
                    print("EVEN REGION", even_region.id, even_region.stats)
                even_region.set_parent(page_even)
                even_region.set_derived_id(page_even.id)
                odd_region.set_parent(page_odd)
                odd_region.set_derived_id(page_odd.id)
                tr_id_map[even_region.id] = text_region.id
                tr_id_map[odd_region.id] = text_region.id
                page_even.add_child(even_region, as_extra=as_extra)
                page_odd.add_child(odd_region, as_extra=as_extra)
        elif text_region.text_regions:
            if debug:
                print("TEXTREGION HAS TEXTREGIONS:", text_region.id)
            even_text_regions = [text_region for text_region in text_region.text_regions if is_even_side(text_region)]
            odd_text_regions = [text_region for text_region in text_region.text_regions if is_odd_side(text_region)]
            if len(even_text_regions) == 0:
                if debug:
                    print("NO EVEN, MOVE TR TO ODD")
                page_odd.add_child(text_region, as_extra=as_extra)
            elif len(odd_text_regions) == 0:
                if debug:
                    print("NO ODD, MOVE TR TO EVEN")
                page_even.add_child(text_region, as_extra=as_extra)
            else:
                # The text region crosses the page boundary. Split the text_regions into new text regions per
                # page, and create new text regions
                if debug:
                    print("SPLIT TEXTREGION")
                odd_region = pdm.PageXMLTextRegion(text_regions=odd_text_regions, metadata=text_region.metadata,
                                                   coords=pdm.parse_derived_coords(odd_text_regions))
                even_region = pdm.PageXMLTextRegion(text_regions=even_text_regions, metadata=text_region.metadata,
                                                    coords=pdm.parse_derived_coords(even_text_regions))
                if debug:
                    print("ODD REGION", odd_region.id, odd_region.stats)
                    print("EVEN REGION", even_region.id, even_region.stats)
                tr_id_map[even_region.id] = text_region.id
                tr_id_map[odd_region.id] = text_region.id
                page_even.add_child(even_region, as_extra=as_extra)
                page_odd.add_child(odd_region, as_extra=as_extra)
        else:
            print('SKIPPING TR', text_region.id)
            # undecided.append(text_region)
            # append_count += 1
        if debug:
            print('APPEND_COUNT:', append_count)
    if debug:
        print('NUM UNDECIDED:', len(undecided))
        for tr in undecided:
            print('\t', tr.id, tr.stats)
    assign_undecided(page_even, page_odd, undecided, page_type_index, debug=debug)
    pages = []
    for page_doc in [page_even, page_odd]:
        if page_doc.coords:
            page_doc.metadata['iiif_url'] = derive_pagexml_page_iiif_url(page_doc.metadata['jpg_url'],
                                                                         page_doc.coords)
        else:
            page_doc.metadata['iiif_url'] = scan_doc.metadata['iiif_url']
        if scan_doc.reading_order:
            # if the scan has a reading order, adopt it for the individual pages
            pagexml_helper.copy_reading_order(scan_doc, page_doc, tr_id_map)
        pages += [page_doc]
    return pages


def assign_undecided(page_even: pdm.PageXMLPage, page_odd: pdm.PageXMLPage,
                     undecided: List[pdm.PageXMLTextRegion],
                     page_type_index: Dict[int, any], debug: bool = False):
    if 'normal_odd_end' in page_odd.metadata:
        for undecided_tr in undecided:
            undecided_tr.metadata['normal_odd_end'] = page_odd.metadata['normal_odd_end']
            undecided_tr.metadata['normal_even_end'] = page_odd.metadata['normal_even_end']
    for page_doc in [page_even, page_odd]:
        if page_doc.metadata['page_num'] not in page_type_index:
            print('missing page_type for page', page_doc.id)
        elif 'title_page' in page_type_index[page_doc.metadata['page_num']]:
            separate_title_lines(page_doc, debug=debug)
        if not page_doc.coords:
            if len(page_doc.columns):
                page_doc.coords = pdm.parse_derived_coords(page_doc.columns)
            elif len(page_doc.text_regions):
                page_doc.coords = pdm.parse_derived_coords(page_doc.text_regions)
            else:
                print("Empty page, no coords")
        decided = []
        if page_doc.coords is None:
            continue
        for undecided_tr in undecided:
            if undecided_tr.coords is None:
                print("Skipping undecided textregion without coords", page_doc.id)
                decided.append(undecided_tr)
            if pdm.is_horizontally_overlapping(undecided_tr, page_doc):
                # print("Adding undecided textregion to page", page_doc.id)
                # print("\tundecided textregion coords:", undecided_tr.coords.box)
                # print("\tundecided textregion stats:", undecided_tr.stats)
                page_doc.add_child(undecided_tr)
                decided.append(undecided_tr)
            elif undecided_tr.coords.left > page_odd.metadata['normal_even_end']:
                page_odd.add_child(undecided_tr)
                decided.append(undecided_tr)
            elif page_odd.metadata['normal_even_end'] - undecided_tr.coords.left < undecided_tr.coords.w:
                page_odd.add_child(undecided_tr)
                decided.append(undecided_tr)
            else:
                page_even.add_child(undecided_tr)
                decided.append(undecided_tr)
        undecided = [tr for tr in undecided if tr not in decided]
    for undecided_tr in undecided:
        if debug:
            print("UNKNOWN:", undecided_tr.id, undecided_tr.stats)
            # print('\tpage_even metadata:', page_even.metadata)
            # print('\tpage_odd metadata:', page_odd.metadata)
            # print('\tundecided metadata:', undecided_tr.metadata)
            undecided_tr.metadata['normal_odd_end'] = page_odd.metadata['normal_odd_end']
            undecided_tr.metadata['normal_even_end'] = page_even.metadata['normal_even_end']
            odd_end, even_end = get_page_split_widths(undecided_tr)
            # print(undecided_tr.parent.metadata)
            print("odd end:", odd_end, "\teven end:", even_end)
            print(undecided_tr.coords.box)
            for line in undecided_tr.lines:
                print(line.coords.x, line.coords.y, line.text)


def split_scan_pages(scan_doc: pdm.PageXMLScan, page_type_index: Dict[int, any] = None,
                     debug: bool = False) -> List[pdm.PageXMLPage]:
    scan_stats = combine_stats([scan_doc])
    pages: List[pdm.PageXMLPage] = []
    if not scan_doc.text_regions:
        return pages
    config = copy.deepcopy(base_config)
    if 3760 <= scan_doc.metadata['inventory_num'] <= 3864:
        max_col_width = 1000
        if scan_doc.metadata['inventory_num'] >= 3804:
            even_page_num = scan_doc.metadata['scan_num'] * 2 - 2
            odd_page_num = scan_doc.metadata['scan_num'] * 2 - 1
            if even_page_num not in page_type_index:
                print(f'missing page_num for page {scan_doc.id}-page-{even_page_num}')
                raise KeyError(f'missing page_type for page {scan_doc.id}-page-{even_page_num}')
            if odd_page_num not in page_type_index:
                print(f'missing page_num for page {scan_doc.id}-page-{odd_page_num}')
                raise KeyError(f'missing page_type for page {scan_doc.id}-page-{odd_page_num}')
            if 'index_page' in page_type_index[even_page_num] or 'index_page' in page_type_index[odd_page_num]:
                max_col_width = 500
                config['column_gap']['gap_pixel_freq_ratio'] = 0.2
                config['column_gap']['gap_threshold'] = 10
    else:
        max_col_width = 2200
    # print("INITIAL EVEN:", page_even.stats)
    # print(page_even.type)
    # print("INITIAL ODD:", page_odd.stats)
    # print(page_odd.type)
    # page_extra = initialize_pagexml_page(scan_doc, 'extra')
    trs = get_column_text_regions(scan_doc, max_col_width, config, debug=debug)
    tr_stats = combine_stats(trs)
    if tr_stats['words'] != scan_stats['words']:
        raise ValueError(f'Unequal number of words in trs ({tr_stats["words"]}) and scan ({scan_stats["words"]})')
    # print('scan_stats:', scan_stats)
    # print('tr_stats:', tr_stats)
    pages = assign_trs_to_odd_even_pages(scan_doc, trs, page_type_index, config, debug=debug)
    page_stats = combine_stats(pages)
    # print('page_stats:', page_stats)
    if page_stats['words'] != scan_stats['words']:
        for page in pages:
            print('stats for page', page.id, page.stats)
        raise ValueError(f'Unequal number of words in pages ({page_stats["words"]}) and scan ({scan_stats["words"]})')
    return pages


def get_column_separator(text_region: pdm.PageXMLTextRegion,
                         separators: List[pdm.PageXMLTextRegion]) -> Union[pdm.PageXMLTextRegion, None]:
    column_separator = None
    for separator in separators:
        sep_left = separator.coords.left - 20
        sep_right = separator.coords.right + 20
        if text_region.coords.left < sep_left and text_region.coords.right > sep_right:
            bottom = min(text_region.coords.bottom, separator.coords.bottom)
            top = max(text_region.coords.top, separator.coords.top)
            overlap = bottom - top
            if overlap / text_region.coords.height > 0.7:
                column_separator = separator
                break
    return column_separator


def split_merged_regions(text_regions: List[pdm.PageXMLTextRegion]) -> List[pdm.PageXMLTextRegion]:
    # ignore really short vertical separators as they are probably not real separators
    separators = [tr for tr in text_regions if tr.has_type('separator') if tr.coords.h > 100]
    split_regions = []
    for tr in text_regions:
        if tr.has_type('extra'):
            split_regions.append(tr)
            continue
        column_separator = get_column_separator(tr, separators)
        if column_separator is not None:
            left_lines, right_lines, extra_lines = [], [], []
            for line in tr.lines:
                if line.coords.right < column_separator.coords.right + 20:
                    left_lines.append(line)
                elif line.coords.left > column_separator.coords.left - 20:
                    right_lines.append(line)
                elif line.coords.bottom < column_separator.coords.top:
                    extra_lines.append(line)
                elif line.coords.top > column_separator.coords.bottom:
                    extra_lines.append(line)
                elif line.coords.bottom < 450 and line.coords.top < column_separator.coords.top:
                    # header line with box overlapping separator box
                    extra_lines.append(line)
                elif line.coords.top > 3150 and line.coords.bottom > column_separator.coords.bottom:
                    # section closing line with box overlapping separator box
                    extra_lines.append(line)
                else:
                    extra_lines.append(line)
                    print('MOVING TO EXTRA', line.id, '\t', line.text)
                    # print('ERROR SEPARATING LINES:')
                    # print('column separator box:', column_separator.coords.box)
                    # print('line box:', line.coords.box)
                    # raise ValueError('cannot sort line to left or right of separator')
            if len(left_lines) > 0:
                left_coords = pdm.parse_derived_coords(left_lines)
                left_tr = pdm.PageXMLTextRegion(lines=left_lines, coords=left_coords, metadata=tr.metadata)
                left_tr.set_derived_id(tr.parent.id)
                split_regions.append(left_tr)
                left_tr.type = tr.type
            if len(right_lines) > 0:
                right_coords = pdm.parse_derived_coords(right_lines)
                right_tr = pdm.PageXMLTextRegion(lines=right_lines, coords=right_coords, metadata=tr.metadata)
                right_tr.set_derived_id(tr.parent.id)
                right_tr.type = tr.type
                split_regions.append(right_tr)
            if len(extra_lines) > 0:
                extra_coords = pdm.parse_derived_coords(extra_lines)
                extra_tr = pdm.PageXMLTextRegion(lines=extra_lines, coords=extra_coords, metadata=tr.metadata)
                extra_tr.set_derived_id(tr.parent.id)
                split_regions.append(extra_tr)
                extra_tr.add_type('extra')
                if extra_tr.has_type('main'):
                    extra_tr.remove_type('main')
                split_regions.append(extra_tr)
        else:
            split_regions.append(tr)
    return split_regions


def separate_title_lines(page: pdm.PageXMLPage, debug: bool = False) -> pdm.PageXMLPage:
    outer: List[pdm.PageXMLDoc] = page.columns + page.text_regions + page.extra
    if 3760 <= page.metadata['inventory_num'] <= 3864:
        max_col_width = 1000
    else:
        max_col_width = 1500
    for tr in outer:
        if debug is True:
            print('\tTEXT REGION', tr.id, tr.type)
        if tr.coords.width > max_col_width:
            if debug is True:
                print('HAS TITLE LINES:', tr.id)
            last_title_line_top = 0
            for line in tr.lines:
                if line.coords.width < max_col_width:
                    continue
                if line.coords.top > 2000:
                    continue
                if debug is True:
                    print('\tTITLE LINE:', line.coords.width, line.coords.top, line.text)
                if line.coords.top > last_title_line_top:
                    last_title_line_top = line.coords.top
                    if debug is True:
                        print('\tLAST TITLE LINE:', line.coords.width, line.coords.top, line.text)
            title_lines = [line for line in tr.lines if line.coords.top <= last_title_line_top]
            col_lines = [line for line in tr.lines if line.coords.top > last_title_line_top]
            if len(title_lines) > 0 and len(col_lines) > 0:
                tr.lines = col_lines
                tr.set_derived_id(page.metadata['scan_id'])
                title_tr_coords = pdm.parse_derived_coords(title_lines)
                title_tr = pdm.PageXMLTextRegion(coords=title_tr_coords, lines=title_lines)
                title_tr.set_derived_id(page.metadata['scan_id'])
                page.extra.append(title_tr)
                if debug is True:
                    print('BELOW TITLE:')
                    for line in tr.lines:
                        print(f'\t{line.coords.left: >4}-{line.coords.right: <4}\t{line.coords.top}\t{line.text}')
    return page


def get_page_full_text_columns(page: pdm.PageXMLPage) -> List[pdm.PageXMLColumn]:
    """Return the full-text columns of a page. Merge any overlapping extra
    columns into the full-text columns."""
    full_text_columns = []
    extra_columns = []
    for column in page.columns:
        try:
            column_type = determine_column_type(column)
        except TypeError:
            column_type = None
        if column_type == 'full_text':
            full_text_columns.append(column)
        elif column_type == 'margin':
            continue
        elif column_type == 'extra_text':
            extra_columns.append(column)
        else:
            continue
    merged_columns = []
    for full_text_col in full_text_columns:
        for extra_col in extra_columns:
            if pagexml_helper.elements_overlap(extra_col, full_text_col):
                # merge columns into new full_text_col
                # make sure multiple merges into the same full text
                # columns are cumulative
                full_text_col = pagexml_helper.merge_columns([extra_col, full_text_col],
                                                             full_text_col.id, full_text_col.metadata)
        # keep tracked of the new merged columns
        merged_columns.append(full_text_col)
    return merged_columns
