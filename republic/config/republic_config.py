import copy
import os
from republic.model.inventory_mapping import get_inventory_by_num, get_inventories_by_year


def set_config_inventory_num(base_config: dict, inventory_num: int, base_dir: str) -> dict:
    config = copy.deepcopy(base_config)
    config["base_dir"] = base_dir
    inv_map = get_inventory_by_num(inventory_num)
    config["year"] = inv_map["year"]
    config["inventory_num"] = inventory_num
    config["hocr_dir"] = os.path.join(config["base_dir"], "hocr/{}/".format(inventory_num))
    config["pagexml_dir"] = os.path.join(config["base_dir"], "PageXML/{}/".format(config["inventory_num"]))
    config["csv_dir"] = os.path.join(config["base_dir"], "csv")
    return config


def set_config_year(base_config: dict, year: int, base_dir: str) -> dict:
    config = copy.deepcopy(base_config)
    config["base_dir"] = base_dir
    inv_map = get_inventories_by_year(year)
    config["year"] = year
    config["inventory_num"] = inv_map["inventory_num"]
    config["hocr_dir"] = os.path.join(config["base_dir"], "hocr/{}/".format(config["inventory_num"]))
    config["pagexml_dir"] = os.path.join(config["base_dir"], "PageXML/{}/".format(config["inventory_num"]))
    config["csv_dir"] = os.path.join(config["base_dir"], "csv")
    return config


base_config = {
    "year": None,
    "inventory_num": None,
    "base_dir": None,
    "inventory_index": "republic_inventory",
    "inventory_doc_type": "inventory",
    "lemma_index": "republic_lemma",
    "lemma_doc_type": "lemma",
    "page_index": "republic_hocr_pages",
    "page_doc_type": "page",
    "scan_index": "republic_hocr_scans",
    "scan_doc_type": "scan",
    "paragraph_index": "republic_paragraphs",
    "paragraph_doc_type": "paragraph",
    "tiny_word_width": 15, # pixel width
    "avg_char_width": 20,
    "remove_tiny_words": True,
    "remove_line_numbers": False,
    "normal_scan_width": 4840,
    "column_gap": {
        "gap_threshold": 50,
        "gap_pixel_freq_ratio": 0.75,
    },
    "word_conf_threshold": 10,
    "fulltext_char_threshold": 0.5,
    "filter_words": ["|", "{", "$", "}", "/", "\\", "[", "]", ";", ":", "(", ")", "!"],
    "index_page": {
        "left_jump_ratio_min": 0.5
    },
    "index_page_early_print": {
        "page_ref_line_threshold": 10,
        "left_jump_ratio_threshold": 0.5,
        "num_words_min": 200,
        "num_words_max": 600,
        "inventory_threshold": 3819,
    },
    "index_page_late_print": {
        "median_line_width_min": 250,
        "median_line_width_max": 400,
        "num_words_min": 200,
        "num_words_max": 500,
        "stdev_line_width_min": 100,
        "stdev_line_width_max": 400,
        "num_lines_min": 130,
        "num_lines_max": 230,
        "num_dates_threshold": 5,
        "num_page_refs_threshold": 15,
        "inventory_threshold": 3798,
        "left_jump_ratio_min": 0.5,
    },
    "resolution_page": {
        "left_jump_ratio_max": 0.3,
        "num_words_min": 700,
        "num_words_max": 1200,
    },
    "respect_page": {
        "column_min_threshold": 3,
        "column_max_threshold": 4,
        "capitalized_word_line_ratio": 0.3,
        "capital_freq_ratio": 0.5,
    },
    "title_page": {
        "min_char_width": 40,
        "min_word_height": 60,
        "min_word_num": 10,
        "num_top_half_words": 60,
        "num_top_half_chars": 150,
        "max_line_width_threshold": 1000,
        "large_word_lines_threshold": 2,
        "title_line_top_threshold": 1300,
        "max_word_num": 500
    }
}

column_config = {
    "avg_char_width": 20,
    "word_conf_threshold": 10,
}


