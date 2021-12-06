import os
import requests
from typing import Dict, Union

from republic.model.inventory_mapping import get_inventory_by_num

HOST_URL = 'https://images.diginfra.net/'


def get_download_urls(uuid: str) -> Dict[str, str]:
    urls = {
        "iiif_url": HOST_URL + "pim/iiifdataset?id=" + uuid,
        "hocr_url": HOST_URL + "api/pim/imageset/annotation/getZippedHocr?imagesetuuid=" + uuid,
        "pagexml_url": HOST_URL + "api/pim/imageset/" + uuid + "/page",
        "zipped_images_url": HOST_URL + "api/pim/imageset/" + uuid + "/zippedimages"
    }
    return urls


def get_inventory_data(url: str) -> Union[bytes, None]:
    response = requests.get(url)
    if response.status_code == 200:
        return response.content
    else:
        return None


def store_inventory_data(inventory_data: bytes, inventory_num: int, ocr_type: str, download_dir: str):
    out_file = get_output_filename(inventory_num, ocr_type, download_dir)
    print(f'\tStoring inventory {inventory_num} {ocr_type} data to {out_file}')
    with open(out_file, 'wb') as fh:
        fh.write(inventory_data)


def get_output_filename(inventory_num: int, ocr_type: str, download_dir: str) -> str:
    data_dir = None
    if ocr_type == "hocr" or ocr_type == "pagexml":
        data_dir = os.path.join(download_dir, ocr_type)
    if data_dir:
        return os.path.join(data_dir, f"{inventory_num}.zip")
    else:
        ValueError("Unknown data type. Must be either 'hocr' or 'pagexml'.")


def download_inventory(inventory_num: int, ocr_type: str, download_dir: str):
    inventory_info = get_inventory_by_num(inventory_num)
    uuid = inventory_info['inventory_uuid']
    try:
        urls = get_download_urls(uuid)
    except (TypeError, KeyError):
        return False
    if ocr_type == "hocr":
        url = urls["hocr_url"]
    elif ocr_type == "pagexml":
        url = urls["pagexml_url"]
        print('download url:', url)
    else:
        raise ValueError("Unknown data type. Must be either 'hocr' or 'pagexml'.")
    inventory_data = get_inventory_data(url)
    if inventory_data:
        store_inventory_data(inventory_data, inventory_num, ocr_type, download_dir)
