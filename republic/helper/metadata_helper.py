from typing import Dict, List, Union

import numpy as np
from settings import image_host_url
from republic.model.inventory_mapping import get_inventory_by_num


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
    if not scan_num:
        raise ValueError('Must use page_num or scan_num')
    scan_num_string = format_scan_number(scan_num)
    viewer_baseurl = f"{image_host_url}/framed3.html"
    jpg_file = "{}_{}_{}.jpg".format(inventory_metadata["series_name"],
                                     inventory_metadata["inventory_num"], scan_num_string)
    jpg_filepath = "{}/{}/{}".format(inventory_metadata["series_name"],
                                     inventory_metadata["inventory_num"], jpg_file)
    jpg_url = image_host_url + "/iiif/{}/{}/{}".format(inventory_metadata["series_name"],
                                                       inventory_metadata["inventory_num"], jpg_file)
    viewer_url = viewer_baseurl + "?imagesetuuid=" + inventory_metadata["inventory_uuid"] + "&uri=" + jpg_url
    return {
        "jpg_url": jpg_url,
        "jpg_filepath": jpg_filepath,
        "iiif_info_url": jpg_url + "/info.json",
        "viewer_url": viewer_url,
        "iiif_url": jpg_url + "/full/full/0/default.jpg"
    }


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
        region = [region[0] - add_margin, region[1] - add_margin, region[2] + 2*add_margin, region[3] + 2*add_margin]
    region = ','.join([str(coord) for coord in region])
    return jpg_url + f"/{region}/full/0/default.jpg"


def coords_to_iiif_url(scan_id: str,
                       coords: Union[List[int], Dict[str, int]] = None, margin=100):
    base_url = f"{image_host_url}/iiif/NL-HaNA_1.01.02/"
    inv_num = scan_id_to_inv_num(scan_id)
    if isinstance(coords, dict):
        coords = [coords["x"], coords["y"], coords["w"], coords["h"]]
    if isinstance(coords, list):
        coords_string = f"{coords[0]-margin},{coords[1]-margin},{coords[2]+2*margin},{coords[3]+2*margin}"
        return f"{base_url}{inv_num}/{scan_id}.jpg/{coords_string}/full/0/default.jpg"
    else:
        return f"{base_url}{inv_num}/{scan_id}.jpg/full/full/0/default.jpg"


def doc_id_to_iiif_url(doc_id: str, margin: int = 100):
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


def get_per_page_type_index(inv_metadata):
    page_type = {page_num: 'empty_page' for page_num in np.arange(inv_metadata['num_pages'])}
    for page_num in inv_metadata['title_page_nums']:
        page_type[page_num] = 'title_page'
    for section in inv_metadata['sections']:
        for page_num in np.arange(section['start'], section['end'] + 1):
            page_type[page_num] = section['page_type']
            if page_num in inv_metadata['title_page_nums']:
                page_type[page_num] = [section['page_type'], 'title_page']
    return page_type


def get_scan_id(inventory_metadata, scan_num):
    scan_num_str = (4 - len(str(scan_num))) * "0" + str(scan_num)
    return f'{inventory_metadata["series_name"]}_{inventory_metadata["inventory_num"]}_{scan_num_str}'


def index_intervention_page_nums(inv_metadata):
    intervene = {
        "inc": {},
        "skip": {},
        "no_num": {},
        "type": {}
    }
    if inv_metadata["page_num_interventions"] is None:
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
        return text_page_num_map
    res_sections = [section for section in inv_metadata["sections"] if section["page_type"] == "resolution_page"]
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
