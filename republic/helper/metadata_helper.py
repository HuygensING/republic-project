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