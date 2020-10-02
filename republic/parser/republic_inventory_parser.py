import os
import zipfile

import republic.parser.republic_file_parser as file_parser
import republic.parser.hocr.republic_page_parser as hocr_page_parser
import republic.parser.pagexml.republic_pagexml_parser as pagexml_parser


def parse_inventory_from_zip(inventory_num: int, inventory_config: dict) -> iter:
    ocr_dir = os.path.join(inventory_config['base_dir'], inventory_config['ocr_type'])
    inv_file = os.path.join(ocr_dir, f'{inventory_num}.zip')
    z = zipfile.ZipFile(inv_file)
    for scan_file in z.namelist():
        with z.open(scan_file) as fh:
            scan_data = fh.read()
            if inventory_config['ocr_type'] == 'hocr':
                scan_info = file_parser.get_scan_info(scan_file, inventory_config['data_dir'])
                scan_doc = hocr_page_parser.get_scan_hocr(scan_info, hocr_data=scan_data, config=inventory_config)
            else:
                scan_doc = pagexml_parser.get_scan_pagexml(scan_file, inventory_config, pagexml_data=scan_data)
            yield scan_doc


def parse_inventory_from_text_repo(inventory_num: int, inventory_config: dict,
                                   inventory_metadata: dict) -> iter:
    ocr_dir = os.path.join(inventory_config['base_dir'], inventory_config['ocr_type'])
    inv_file = os.path.join(ocr_dir, f'{inventory_num}.zip')
    z = zipfile.ZipFile(inv_file)
    for scan_file in z.namelist():
        with z.open(scan_file) as fh:
            scan_data = fh.read()
            if inventory_config['ocr_type'] == 'hocr':
                scan_info = file_parser.get_scan_info(scan_file, inventory_config['data_dir'])
                scan_doc = hocr_page_parser.get_scan_hocr(scan_info, hocr_data=scan_data, config=inventory_config)
            else:
                scan_doc = pagexml_parser.get_scan_pagexml(scan_file, inventory_config, pagexml_data=scan_data)
            yield scan_doc
