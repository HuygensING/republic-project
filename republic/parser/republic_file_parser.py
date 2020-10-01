import os
import glob
import xmltodict
from typing import Union, List, Dict
from collections import defaultdict
from republic.model.inventory_mapping import inventory_mapping, get_inventory_by_num
from republic.helper.metadata_helper import format_scan_number, make_scan_urls
from republic.parser.hocr.generic_hocr_parser import make_hocr_doc
from republic.parser.hocr.republic_index_page_parser import count_page_ref_lines


# column split filename format: NL-HaNA_1.01.02_3780_0016.jpg-0-251-98--0.40.hocr
# filename hOCR format: NL-HaNA_1.01.02_3780_0016.jpg.hocr
# filename PageXML format: NL-HaNA_1.01.02_3780_0016.jpg.page.xml

OCR_FILE_TYPES = ['.hocr', '.page.xml']
ocr_type_file_extensions = {
    'hocr': '.hocr',
    'pagexml': '.page.xml'
}


#####################
# Generic functions #
#####################


def get_ocr_type(filename: str) -> str:
    for ocr_type in ocr_type_file_extensions:
        if filename.endswith(ocr_type_file_extensions[ocr_type]):
            return ocr_type
    raise ValueError('Unknown OCR type file extension')


def get_republic_scan_metadata(scan_file: str) -> dict:
    _scan_dir, scan_fname = os.path.split(scan_file)
    _, inv_num, scan_num = [int(part) for part in scan_fname.split('.')[2].split('_')]
    inv_info = get_inventory_by_num(inv_num)
    ocr_type = get_ocr_type(scan_file)
    inv_period = get_inventory_period(scan_file)
    urls = make_scan_urls(inv_info, scan_num=scan_num)
    return {
        'series_name': inv_info['series_name'],
        'series_uuid': inv_info['series_uuid'],
        'inventory_uuid': inv_info['inventory_uuid'],
        'inventory_num': inv_num,
        'inventory_year': inv_info['year'],
        'inventory_period_start': inv_period[0],
        'inventory_period_end': inv_period[1],
        'scan_file': scan_file,
        'scan_num': scan_num,
        'ocr_type': ocr_type,
        'doc_type': 'scan',
        'scan_id': f'{inv_info["series_name"]}_{inv_num}_{format_scan_number(scan_num)}',
        'viewer_url': urls['viewer_url'],
        'jpg_url': urls['jpg_url'],
        'iiif_url': urls['iiif_url']
    }


#####################
# PageXML functions #
#####################


def read_pagexml_file(pagexml_file: str, pagexml_data: Union[str, None] = None) -> dict:
    if pagexml_data:
        return xmltodict.parse(pagexml_data)
    with open(pagexml_file, 'rt') as fh:
        data = xmltodict.parse(fh.read())
        return data


def get_pagexml_files(pagexml_dir: str) -> List[str]:
    return glob.glob(os.path.join(pagexml_dir, "*.xml"))


##################
# hOCR functions #
##################


def is_ocr_file(fname: str) -> bool:
    """make sure only OCR files are included"""
    for file_type in OCR_FILE_TYPES:
        if fname[-len(file_type):] == file_type:
            return True
    return False


def get_hocr_files(data_dir: str) -> list:
    for root_dir, sub_dirs, filenames in os.walk(data_dir):
        scan_info = [get_scan_info(fname, root_dir) for fname in filenames if is_ocr_file(fname)]
        if "scan_num_column_num" in scan_info[0]:
            return sorted(scan_info, key=lambda x: x["scan_num_column_num"])
        else:
            return sorted(scan_info, key=lambda x: x["scan_num"])


def read_hocr_scan(scan_file: dict, config) -> Union[int, None]:
    _column_id = "{}-{}".format(scan_file["scan_num"], scan_file["scan_column"])
    hocr_doc = make_hocr_doc(scan_file["filepath"], doc_id=scan_file["page_num"], config=config)
    if not hocr_doc:
        return None
    hocr_doc.scan_info = scan_file
    hocr_doc.scan_info["num_page_ref_lines"] = count_page_ref_lines(hocr_doc)
    return hocr_doc


def get_scan_num(fname: str) -> int:
    return int(fname.split(".")[2].split("_")[2])


def get_inventory_num(fname: str) -> int:
    fname_parts = fname.split(".")
    return int(fname_parts[2].split("_")[1])


def get_inventory_period(fname: str) -> Union[str, None]:
    inventory_num = get_inventory_num(fname)
    for inventory_map in inventory_mapping:
        if inventory_num == inventory_map["inventory_num"]:
            return inventory_map["period"]
    else:
        return None


def get_inventory_year(fname: str) -> Union[int, None]:
    inventory_num = get_inventory_num(fname)
    for inventory in inventory_mapping:
        if inventory_num == inventory["inventory_num"]:
            return inventory["year"]
    else:
        return None


def get_column_num(fname: str) -> int:
    fname_parts = fname.split(".")
    if fname_parts[3] == "hocr":
        # file is whole page, not individual column
        return 1
    elif fname_parts[3].startswith("jpg-"):
        return int(fname_parts[3].split("-")[1])
    else:
        raise TypeError("Unexpected structure of filename")


def get_scan_page_num(fname: str) -> int:
    page_num = get_scan_num(fname) * 2 - 2
    if get_page_side(fname) == "odd":
        page_num += 1
    return page_num


def get_scan_slant(fname: str) -> Union[float, None]:
    fname_parts = fname.split(".")
    if fname_parts[3] == "hocr":
        # file is whole page, not individual column
        return None
    column_parts = fname_parts[3].split("-")
    if len(column_parts) == 6:
        return float(column_parts[5]) * -1
    elif len(column_parts) == 5:
        return float(column_parts[4])
    else:
        raise TypeError("Unexpected structure of filename")


def get_page_side(fname: str) -> str:
    parts = fname.split(".")[3].split("-")
    if int(parts[2]) < 2200:
        return "even"
    else:
        return "odd"


def has_single_column_file(fname: str) -> bool:
    fname_parts = fname.split(".")
    # file is whole page, not individual column
    return fname_parts[3].startswith("jpg")


def get_scan_info(fname: str, root_dir: str) -> dict:
    if has_single_column_file(fname):
        return get_scan_info_column(fname, root_dir)
    else:
        return get_republic_scan_metadata(fname)


def get_scan_info_column(fname: str, root_dir: str) -> dict:
    return {
        "scan_num": get_scan_num(fname),
        "scan_column": get_column_num(fname),
        "scan_num_column_num": get_scan_num(fname) + 0.1 * get_column_num(fname),
        "inventory_num": get_inventory_num(fname),
        "inventory_year": get_inventory_year(fname),
        "inventory_period": get_inventory_period(fname),
        "page_id": "inventory-{}-scan-{}-page-{}".format(get_inventory_num(fname), get_scan_num(fname), get_scan_page_num(fname)),
        "page_num": get_scan_page_num(fname),
        "page_side": get_page_side(fname),
        "slant": get_scan_slant(fname),
        "column_id": "scan-{}-{}-{}".format(get_scan_num(fname), get_scan_page_num(fname), get_column_num(fname)),
        "filepath": os.path.join(root_dir, fname)
    }


def get_scan_info_double_page(fname: str, root_dir: str) -> dict:
    return {
        "scan_num": get_scan_num(fname),
        "inventory_num": get_inventory_num(fname),
        "inventory_year": get_inventory_year(fname),
        "inventory_period": get_inventory_period(fname),
        "filepath": os.path.join(root_dir, fname)
    }


def make_page_info(scan_file: dict) -> dict:
    return {
        "scan_num": scan_file["scan_num"],
        "inventory_num": scan_file["inventory_num"],
        "inventory_year": scan_file["inventory_year"],
        "inventory_period": scan_file["inventory_period"],
        "page_id": scan_file["page_id"],
        "page_num": scan_file["page_num"],
        "page_side": scan_file["page_side"],
        "columns": []
    }


def gather_page_columns(scan_files: list) -> defaultdict:
    page_info = defaultdict(list)
    for scan_file in scan_files:
        if scan_file["page_id"] not in page_info:
            page_info[scan_file["page_id"]] = make_page_info(scan_file)
        page_info[scan_file["page_id"]]["columns"] += [scan_file]
    return page_info
