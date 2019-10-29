import copy
import os
from model.inventory_mapping import get_inventory_by_num, get_inventory_by_year


def set_config_inventory_num(base_config: dict, inventory_num: int, base_dir: str) -> dict:
    config = copy.deepcopy(base_config)
    config["base_dir"] = base_dir
    inv_map = get_inventory_by_num(inventory_num)
    config["year"] = inv_map["year"]
    config["inventory_num"] = inventory_num
    config["data_dir"] = os.path.join(config["base_dir"], "{}/".format(inventory_num))
    return config


def set_config_year(base_config: dict, year: int, base_dir: str) -> dict:
    config = copy.deepcopy(base_config)
    config["base_dir"] = base_dir
    inv_map = get_inventory_by_year(year)
    config["year"] = year
    config["inventory_num"] = inv_map["inventory_num"]
    config["data_dir"] = os.path.join(config["base_dir"], "{}/".format(year))
    return config


base_config = {
    "year": None,
    "inventory_num": None,
    "base_dir": None,
    "page_index": "republic_hocr_pages",
    "page_doc_type": "page",
    "scan_index": "republic_hocr_scans",
    "scan_doc_type": "scan",
    "tiny_word_width": 15, # pixel width
    "avg_char_width": 20,
    "remove_tiny_words": True,
    "remove_line_numbers": False,
    "normal_scan_width": 4840,
    "word_conf_threshold": 10,
    "column_gap_threshold": 50,
    "gap_pixel_freq_ratio": 0.75,
    "fulltext_char_threshold": 0.5,
    "fulltext_words_threshold": 15,
    "filter_words": ["|", "{", "$"]
}

column_config = {
    "avg_char_width": 20,
    "word_conf_threshold": 10,
    "column_gap_threshold": 50,
    "gap_pixel_freq_ratio": 0.75,
    "fulltext_char_threshold": 0.5,
    "fulltext_words_threshold": 15,
    "filter_words": ["|", "{", "$"]
}


