import os
import requests
from elasticsearch import Elasticsearch
from typing import Dict, Union
from settings import set_elasticsearch_config

from republic.analyser.republic_inventory_analyser import get_inventory_uuid

elasticsearch_config = set_elasticsearch_config()
HOST_URL = elasticsearch_config["data_host"]["host_url"]


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


def store_inventory_data(inventory_data: bytes, inventory_num: int, ocr_type: str, inventory_config: dict):
    out_file = get_output_filename(inventory_num, ocr_type, inventory_config)
    print(f'\tStoring inventory {inventory_num} {ocr_type} data to {out_file}')
    with open(out_file, 'wb') as fh:
        fh.write(inventory_data)


def get_output_filename(inventory_num: int, ocr_type: str, inventory_config: dict) -> str:
    data_dir = None
    if ocr_type == "hocr" or ocr_type == "pagexml":
        data_dir = os.path.join(inventory_config["base_dir"], ocr_type)
    if data_dir:
        return os.path.join(data_dir, f"{inventory_num}.zip")
    else:
        ValueError("Unknown data type. Must be either 'hocr' or 'pagexml'.")


def download_inventory(es: Elasticsearch, inventory_num: int, ocr_type: str, inventory_config: dict):
    uuid = get_inventory_uuid(es, inventory_num, inventory_config)
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
        store_inventory_data(inventory_data, inventory_num, ocr_type, inventory_config)

