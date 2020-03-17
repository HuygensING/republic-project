from typing import Dict, List, Union


def make_scan_urls(inventory_metadata: dict,
                   page_num: Union[None, int] = None,
                   scan_num: Union[None, int] = None) -> Dict[str, str]:
    if page_num:
        scan_num = int(page_num / 2) + 1
    if not scan_num:
        raise ValueError('Must use page_num or scan_num')
    scan_num_string = format_scan_number(scan_num)
    viewer_baseurl = "https://images.diginfra.net/framed3.html"
    jpg_file = "{}_{}_{}.jpg".format(inventory_metadata["series_name"],
                                     inventory_metadata["inventory_num"], scan_num_string)
    jpg_url = "https://images.diginfra.net/iiif/{}/{}/{}".format(inventory_metadata["series_name"],
                                                                 inventory_metadata["inventory_num"], jpg_file)
    viewer_url = viewer_baseurl + "?imagesetuuid=" + inventory_metadata["inventory_uuid"] + "&uri=" + jpg_url
    return {
        "jpg_url": jpg_url,
        "iiif_info_url": jpg_url + "/info.json",
        "viewer_url": viewer_url,
        "iiif_url": jpg_url + "/full/full/0/default.jpg"
    }


def make_iiif_region_url(jpg_url: str, region: Union[None, List[int], Dict[str, int]] = None) -> str:
    if None:
        region = "full"
    elif isinstance(region, list):
        if len(region) != 4:
            raise IndexError('Region as list of coordinates must have four integers [x, y, w, h]')
        for item in region:
            if not isinstance(item, int):
                raise ValueError('Region as list of coordinates must be integers')
        region = ','.join(region)
    elif isinstance(region, dict):
        keys = ['left', 'top', 'width', 'height']
        region = ','.join([str(region[key]) for key in keys])
    else:
        raise ValueError('region must be None, list of 4 integers, of dict with keys "left", "top", "width", "height"')
    return jpg_url + f"/{region}/full/0/default.jpg"


def format_scan_number(scan_num: int) -> str:
    add_zeroes = 4 - len(str(scan_num))
    return "0" * add_zeroes + str(scan_num)
