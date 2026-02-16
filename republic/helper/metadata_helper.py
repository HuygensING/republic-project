import json
from collections import defaultdict
from collections import Counter
from typing import Dict, List, Union, Set, Tuple

import numpy as np
import pagexml.model.physical_document_model as pdm

from settings import image_host_url
from republic.model.inventory_mapping import get_inventory_by_num


KNOWN_TYPES = {
    'marginalia': 0,
    'date': 1,
    'attendance': 2,
    'date_header': 3,
    'page_number': 4,
    'resolution': 5,
    'noise': 6,
    'empty': 7
}


def make_scan_urls(inventory_metadata: dict = None, inventory_num: int = None,
                   page_num: int = None,
                   scan_num: int = None,
                   scan_id: str = None) -> Dict[str, str]:
    if inventory_num:
        inventory_metadata = get_inventory_by_num(inventory_num)
    if scan_id:
        scan_num = int(scan_id.split('_')[-1])
    if page_num:
        scan_num = int(page_num / 2) + 1
    if scan_num is None:
        raise ValueError('Must use page_num or scan_num')
    scan_num_string = format_scan_number(scan_num)
    viewer_baseurl = f"{image_host_url}/framed3.html"
    jpg_file = "{}_{}_{}.jpg".format(inventory_metadata["series_name"],
                                     inventory_metadata["inventory_num"], scan_num_string)
    jpg_filepath = "{}/{}/{}".format(inventory_metadata["series_name"],
                                     inventory_metadata["inventory_num"], jpg_file)
    jpg_url = image_host_url + "/iiif/{}/{}/{}".format(inventory_metadata["series_name"],
                                                       inventory_metadata["inventory_num"], jpg_file)
    if 'inventory_uuid' in inventory_metadata and inventory_metadata['inventory_uuid'] is not None:
        viewer_url = viewer_baseurl + "?imagesetuuid=" + inventory_metadata["inventory_uuid"] + "&uri=" + jpg_url
    else:
        viewer_url = None
    return {
        "jpg_url": jpg_url,
        "jpg_filepath": jpg_filepath,
        "iiif_info_url": jpg_url + "/info.json",
        "viewer_url": viewer_url,
        "iiif_url": jpg_url + "/full/full/0/default.jpg"
    }


def update_region_with_margin(region: List[int], add_margin: int) -> List[int]:
    return [
        region[0] - add_margin if region[0] > add_margin else 0,
        region[1] - add_margin if region[1] > add_margin else 0,
        region[2] + 2 * add_margin,
        region[3] + 2 * add_margin
    ]


def make_iiif_region_url(jpg_url: str,
                         region: Union[None, List[int], Dict[str, int]] = None,
                         add_margin: Union[None, int] = None) -> str:
    if region is None:
        return jpg_url + f"/full/full/0/default.jpg"
    elif isinstance(region, dict):
        if 'left' in region:
            region = [region['left'], region['top'], region['width'], region['height']]
        else:
            region = [region['x'], region['y'], region['w'], region['h']]
    elif isinstance(region, list):
        if len(region) != 4:
            raise IndexError('Region as list of coordinates must have four integers [x, y, w, h]')
        for item in region:
            if not isinstance(item, int):
                raise ValueError('Region as list of coordinates must be integers')
    else:
        print('invalid region:', region)
        raise ValueError('region must be None, list of 4 integers, of dict with keys "left", "top", "width", "height"')
    if add_margin:
        region = update_region_with_margin(region, add_margin)
    region = ','.join([str(coord) for coord in region])
    return jpg_url + f"/{region}/full/0/default.jpg"


def coords_to_iiif_url(scan_id: str,
                       coords: Union[List[int], Dict[str, int], pdm.Coords] = None, margin=100,
                       size: Union[str, Tuple[int, int]] = 'full'):
    try:
        if 'NL-HaNA_1.01.02' in scan_id:
            base_url = f"{image_host_url}/iiif/NL-HaNA_1.01.02/"
            inv_num = scan_id_to_inv_num(scan_id)
        if 'NL-HaNA_1.10.94' in scan_id:
            base_url = f"{image_host_url}/iiif/NL-HaNA_1.10.94/"
            inv_num = scan_id_to_inv_num(scan_id)
        elif 'KB_series' in scan_id:
            base_url = f"{image_host_url}/iiif/KB_series/"
            inv_num = scan_id.split('_')[2]
    except BaseException:
        print(f"coords_to_iiif_url: invalid scan id: {scan_id}")
        raise
    if isinstance(size, str):
        size_string = size
    else:
        width = size[0] if isinstance(size[0], int) else ''
        height = size[1] if isinstance(size[1], int) else ''
        size_string= f"{width},{height}"
    if isinstance(coords, pdm.Coords):
        coords = [coords.x, coords.y, coords.w, coords.h]
    elif isinstance(coords, dict):
        coords = [coords["x"], coords["y"], coords["w"], coords["h"]]
    if isinstance(coords, list):
        x = coords[0] - margin if coords[0] > margin else 0
        y = coords[1] - margin if coords[1] > margin else 0
        coords_string = f"{x},{y},{coords[2]+2*margin},{coords[3]+2*margin}"
        return f"{base_url}{inv_num}/{scan_id}.jpg/{coords_string}/{size_string}/0/default.jpg"
    else:
        return f"{base_url}{inv_num}/{scan_id}.jpg/full/{size_string}/0/default.jpg"


def doc_id_to_iiif_url(doc_id: str, margin: int = 100, size: Union[str, Tuple[int, int]] = 'full'):
    coord_types = {'column', 'text_region', 'line'}
    coords = None
    page_num = None
    is_coord_type = None
    for coord_type in coord_types:
        if f'-{coord_type}-' in doc_id:
            is_coord_type = coord_type
    if is_coord_type:
        scan_id, type_coords = doc_id.split(f'-{is_coord_type}-')
        coords = [int(coord) for coord in type_coords.split('-')]
    elif '-page-' in doc_id:
        scan_id, page_num = doc_id.split(f'-page-')
    else:
        scan_id = doc_id
    if coords is not None:
        return coords_to_iiif_url(scan_id, coords, margin=margin)
    if page_num is not None:
        x = 2400 if int(page_num) % 2 == 1 else 0
        coords = [x, 0, 2500, 3500]
        return coords_to_iiif_url(scan_id, coords, margin=margin)
    else:
        return coords_to_iiif_url(scan_id)


def page_num_to_page_id(page_num: int, inv_num: int) -> str:
    scan_num = int((page_num + 1) / 2) if page_num % 2 == 1 else int((page_num + 2) / 2)
    scan_id = f'NL-HaNA_1.01.02_{inv_num}_{format_scan_number(scan_num)}'
    return f'{scan_id}-page-{page_num}'


def scan_id_to_inv_num(scan_id: str) -> int:
    return int(scan_id.split('_')[2])


def format_scan_number(scan_num: int) -> str:
    add_zeroes = 4 - len(str(scan_num))
    return "0" * add_zeroes + str(scan_num)


def correct_section_types(inv_metadata):
    section_starts = {offsets['page_num_offset']: offsets['page_type'] for offsets in
                      inv_metadata['type_page_num_offsets']}
    for section in inv_metadata['sections']:
        if section['start'] in section_starts:
            section['page_type'] = section_starts[section['start']]
    return None


def get_per_page_type_index(inv_metadata: Dict[str, any]) -> Dict[int, Union[str, List[str]]]:
    if "num_pages" not in inv_metadata:
        print(f'Warning: num_pages property is missing for inventory {inv_metadata["inventory_num"]}')
        return {}
    if inv_metadata['num_pages'] is None:
        if inv_metadata['num_scans'] is None:
            print(f'Warning: num_pages and num_scan properties are None for '
                  f'inventory {inv_metadata["inventory_num"]}')
            return {}
        print(f'Warning: num_pages property is None for inventory {inv_metadata["inventory_num"]}, using num_scans')
        inv_metadata['num_pages'] = inv_metadata['num_scans'] * 2 + 2
    page_type = {page_num: 'unknown' for page_num in np.arange(inv_metadata['num_pages'] + 1)}
    title_page_nums = inv_metadata['title_page_nums'] if 'title_page_nums' in inv_metadata else []
    sections = inv_metadata['sections'] if 'sections' in inv_metadata else []
    for section in sections:
        for page_num in np.arange(section['start'], section['end'] + 1):
            page_type[page_num] = section['page_type']
            if page_num in title_page_nums:
                page_type[page_num] = [section['page_type'], 'title_page']
    return page_type


def get_scan_id(inventory_metadata: dict, scan_num: int):
    scan_num_str = (4 - len(str(scan_num))) * "0" + str(scan_num)
    return f'{inventory_metadata["series_name"]}_{inventory_metadata["inventory_num"]}_{scan_num_str}'


def parse_scan_id(scan_id: str):
    # example: NL-HaNA_1.01.02_3820_0079
    try:
        series_prefix, series_num, inventory_num, scan_num = scan_id.split('_')
    except ValueError:
        raise
    if len(scan_num) != 4:
        raise ValueError(f'Invalid scan id: {scan_id}')
    return {
        "series_prefix": series_prefix,
        "series_num": series_num,
        "series": f"{series_prefix}_{series_num}",
        "inventory_num": int(inventory_num),
        "scan_num": int(scan_num),
        "scan_id": scan_id
    }


def index_intervention_page_nums(inv_metadata):
    intervene = {
        "inc": {},
        "skip": {},
        "no_num": {},
        "type": {}
    }
    if "page_num_interventions" not in inv_metadata or inv_metadata["page_num_interventions"] is None:
        return intervene
    for intervention in inv_metadata["page_num_interventions"]:
        page_num = intervention["page_num_offset"]
        if intervention["intervention_type"] == "increment":
            intervene["inc"][page_num] = intervention["text_page_num_increment"]
        elif intervention["intervention_type"] == "skip":
            for page_num in range(intervention["page_num_offset"], intervention["page_num_end"] + 1):
                intervene["skip"][page_num] = True
                intervene["type"][page_num] = intervention["problem_type"]
        elif intervention["intervention_type"] == "no_page_num":
            for page_num in range(intervention["page_num_offset"], intervention["page_num_end"] + 1):
                intervene["no_num"][page_num] = True
                intervene["type"][page_num] = intervention["problem_type"]
    return intervene


def map_text_page_nums(inv_metadata: dict) -> Dict[int, Dict[str, Union[int, str]]]:
    text_page_num_map = {}
    if "sections" not in inv_metadata:
        print(f"no sections for inventory {inv_metadata['inventory_num']}")
        return text_page_num_map
    res_sections = [section for section in inv_metadata["sections"] if section["page_type"] == "resolution_page"]
    # print(f"res_sections: {res_sections}")
    intervene = index_intervention_page_nums(inv_metadata)
    for section in res_sections:
        if "text_page_num" not in section:
            # skip section if we don't know text page numbers yet
            continue
        text_page_num = section["text_page_num"]
        for page_num in range(section["start"], section["end"]+1):
            skip = False
            problem = intervene["type"][page_num] if page_num in intervene["type"] else None
            if page_num in intervene["inc"]:
                text_page_num += intervene["inc"][page_num]
            if page_num in intervene["skip"]:
                curr_page_num = None
                skip = True
            elif page_num in intervene["no_num"]:
                curr_page_num = None
            else:
                curr_page_num = text_page_num
            text_page_num += 1
            text_page_num_map[page_num] = {
                "text_page_num": curr_page_num,
                "problem": problem,
                "skip": skip
            }
    return text_page_num_map


def load_greffiers():
    greffier_file = '../../data/attendance_lists/griffiers.json'
    with open(greffier_file, 'rt') as fh:
        return json.load(fh)


def get_scan_id_from_element_id(line_id: str):
    return line_id.split('-line-')[0]


def group_line_ranges_by_scan(line_ranges):
    scan_line_ranges = defaultdict(list)
    for lr in line_ranges:
        scan_id = get_scan_id_from_element_id(lr['line_id'])
        scan_line_ranges[scan_id].append(lr)
    return scan_line_ranges


def get_line_id_bbox(line_id: str):
    x, y, w, h = [int(ele) for ele in line_id.split('-')[-4:]]
    return {'x': x, 'y': y, 'w': w, 'h': h, 'left': x, 'right': x+w, 'top': y, 'bottom': y+h}


def get_line_ranges_bbox(line_ranges):
    bboxes = [get_line_id_bbox(lr['line_id']) for lr in line_ranges]
    left = min([bbox['left'] for bbox in bboxes])
    right = max([bbox['right'] for bbox in bboxes])
    top = min([bbox['top'] for bbox in bboxes])
    bottom = max([bbox['bottom'] for bbox in bboxes])
    return {'x': left, 'y': top, 'w': right-left, 'h': bottom-top,
            'left': left, 'right': right, 'top': top, 'bottom': bottom}


def get_para_tr_iiif_urls(para):
    tr_iiif_urls = []
    scan_line_ranges = group_line_ranges_by_scan(para.line_ranges)
    for scan_id in scan_line_ranges:
        bbox = get_line_ranges_bbox(scan_line_ranges[scan_id])
        tr_iiif_url = coords_to_iiif_url(scan_id, bbox)
        tr_iiif_urls.append(tr_iiif_url)
    return tr_iiif_urls


def get_resolution_sections(inv_meta: Dict[str, any]) -> List[Dict[str, any]]:
    if 'sections' not in inv_meta or len(inv_meta['sections']) == 0:
        return []
    return [section for section in inv_meta['sections'] if section['page_type'] == 'resolution_page']


def get_resolution_page_nums(inv_meta: Dict[str, any]):
    res_sections = get_resolution_sections(inv_meta)
    return [pn for sec in res_sections for pn in range(sec['start'], sec['end'] + 1)]


def map_line_class_to_tr_class(line_class: str):
    lc_map = {
        'para_mid': 'resolution',
        'para_start': 'resolution',
        'para_end': 'resolution'
    }
    return lc_map[line_class] if line_class in lc_map else line_class


def get_line_class_dist(lines: List[pdm.PageXMLTextLine]) -> Counter:
    """Count the frequency of line classes for a list of lines"""
    lcs = [map_line_class_to_tr_class(line.metadata['line_class']) for line in lines]
    return Counter(lcs)


def get_majority_line_class(lines: List[pdm.PageXMLTextLine], debug: int = 0) -> Union[str, None]:
    """Return the most frequent line class for a list of lines. When there are
    multiple most frequent line classes, pick the first in order of known types.

    Assumption: the line classes are sorted by specificity. If a list of lines has
    equal numbers of lines with date and with resolution, assume that date is the
    more relevant one."""
    lc_freq = get_line_class_dist(lines)
    max_freq = max(lc_freq.values())
    max_classes = [lc for lc in lc_freq if lc_freq[lc] == max_freq]
    if debug > 0:
        print(f"metadata_helper.get_majority_line_class - lc_freq: {lc_freq}")
        print(f"    max_classes: {max_classes}")
    for known_type in KNOWN_TYPES:
        if known_type in max_classes:
            return known_type
    if 'title' in max_classes or 'insert_omitted' in max_classes or 'table' in max_classes:
        return 'resolution'
    if 'unknown' in max_classes:
        # if the majority class is unknown, assume the text region is an
        # instance of the most common class, resolution
        return 'resolution'
    return None


def get_tr_known_types(tr: pdm.PageXMLTextRegion) -> Set[str]:
    return set([tr_type for tr_type in KNOWN_TYPES if tr.has_type(tr_type)])
