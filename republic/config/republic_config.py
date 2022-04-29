import copy
import os
from typing import Union
from republic.model.inventory_mapping import get_inventory_by_num


def get_base_config(inventory_num: int = None):
    config = copy.deepcopy(base_config)
    set_inventory_indexes(config)
    if inventory_num:
        set_inventory_metadata(inventory_num, config)
        set_inventory_period_elements(inventory_num, config)
    return config


def set_config_inventory_num(inventory_num: int, ocr_type: str,
                             default_config: Union[None, dict] = None,
                             base_dir: Union[None, str] = None) -> dict:
    if default_config is None:
        default_config = base_config
    config = copy.deepcopy(default_config)
    set_inventory_base_dir(ocr_type, base_dir, config)
    set_inventory_metadata(inventory_num, config)
    set_inventory_indexes(config)
    set_inventory_period_elements(inventory_num, config)
    return config


def set_inventory_base_dir(ocr_type: str, base_dir: str, config: dict) -> None:
    assert(ocr_type == 'hocr' or ocr_type == 'pagexml')
    config['ocr_type'] = ocr_type
    if base_dir:
        config['base_dir'] = base_dir
        config['data_dir'] = os.path.join(config['base_dir'], 'data')
        config['csv_dir'] = os.path.join(config['base_dir'], 'csv')


def set_inventory_metadata(inventory_num: int, config: dict) -> None:
    inv_map = get_inventory_by_num(inventory_num)
    for field in inv_map:
        config[field] = inv_map[field]
    config['year'] = inv_map['year']
    config['inventory_num'] = inventory_num


def set_inventory_indexes(config: dict) -> None:
    # config['page_index'] = f'{ocr_type}_pages'
    # config['scan_index'] = f'{ocr_type}_scans'
    config['page_index'] = 'pages'
    config['scan_index'] = 'scans'
    config['paragraph_index'] = 'paragraphs'
    config['session_index'] = 'sessions'
    config['session_lines_index'] = 'session_lines'
    config['session_text_index'] = 'session_text'
    config['resolution_index'] = 'resolutions'
    config['session_doc_type'] = 'session'
    config['phrase_match_index'] = 'phrase_matches'
    config['resolution_metadata_index'] = 'resolution_metadata'


def set_inventory_period_elements(inventory_num: int, config: dict):
    layout_elements = ['resolution_layout', 'index_layout', 'respecten_layout']
    for layout_element in layout_elements:
        for period in layout_periods[layout_element]:
            if period['inventory_start'] <= inventory_num <= period['inventory_end']:
                config[layout_element] = period['layout_type']
    for period in spelling_periods:
        if period['inventory_start'] <= inventory_num <= period['inventory_end']:
            config['spelling_period'] = period


layout_periods = {
    'resolution_layout': [
        {
            'layout_type': 'use_indent',
            "inventory_start": 3760,
            "inventory_end": 3765,
            "year_start": 1705,
            "year_end": 1710
        },
        {
            'layout_type': 'use_vertical_space',
            "inventory_start": 3766,
            "inventory_end": 3864,
            "year_start": 1711,
            "year_end": 1796
        },
    ],
    'index_layout': [
        {
            'layout_type': 'single_column_no_repeat',
            "inventory_start": 3760,
            "inventory_end": 3762,
            "year_start": 1705,
            "year_end": 1707
        },
        {
            'layout_type': 'single_column_repeat_symbol',
            "inventory_start": 3763,
            "inventory_end": 3804,
            "year_start": 1708,
            "year_end": 1749
        },
        {
            'layout_type': 'three_column',
            "inventory_start": 3805,
            "inventory_end": 3809,
            "year_start": 1750,
            "year_end": 1754
        },
        {
            'layout_type': 'four_column',
            "inventory_start": 3810,
            "inventory_end": 3864,
            "year_start": 1755,
            "year_end": 1796
        },
    ],
    'respecten_layout': [
        {
            'layout_type': 'no_respecten',
            "inventory_start": 3760,
            "inventory_end": 3795,
            "year_start": 1705,
            "year_end": 1740
        },
        {
            'layout_type': 'four_column_respecten',
            "inventory_start": 3796,
            "inventory_end": 3798,
            "year_start": 1741,
            "year_end": 1743
        },
        {
            'layout_type': 'three_column_respecten',
            "inventory_start": 3799,
            "inventory_end": 3864,
            "year_start": 1744,
            "year_end": 1796
        },
    ],
}


spelling_periods = [
    {
        'period_start': 1705,
        'period_end': 1716,
        'inventory_start': 3760,
        'inventory_end': 3771,
        'spelling': 'ae_ck_ey_gh'
    },
    {
        'period_start': 1717,
        'period_end': 1749,
        'inventory_start': 3772,
        'inventory_end': 3804,
        'spelling': 'aa_ck_ey_gh'
    },
    {
        'period_start': 1750,
        'period_end': 1764,
        'inventory_start': 3805,
        'inventory_end': 3819,
        'spelling': 'aa_ck_ei_gh'
    },
    {
        'period_start': 1765,
        'period_end': 1796,
        'inventory_start': 3820,
        'inventory_end': 3864,
        'spelling': 'aa_k_ei_g'
    },
]


base_config = {
    'year': None,
    'inventory_num': None,
    'base_dir': None,
    'ocr_type': 'pagexml',
    'inventory_index': 'republic_inventory',
    'inventory_doc_type': 'inventory',
    'lemma_index': 'lemma_reference',
    'scans_index': 'scans',
    'pages_index': 'pages',
    'resolutions_index': 'resolutions',
    'session_lines_index': 'session_lines',
    'session_text_index': 'session_text',
    'phrase_matches_index': 'phrase_matches',
    # width numbers are pixel width
    'tiny_word_width': 15,
    'avg_char_width': 20,
    'remove_tiny_words': True,
    'remove_line_numbers': False,
    'normal_scan_width': 4840,
    'column_gap': {
        'gap_threshold': 50,
        'gap_pixel_freq_ratio': 0.75,
    },
    'word_conf_threshold': 10,
    'fulltext_char_threshold': 0.5,
    'filter_words': ['|', '{', '$', '}', '/', '\\', '[', ']', ';', ':', '(', ')', '!'],
    'index_page': {
        'left_jump_ratio_min': 0.5
    },
    'index_page_early_print': {
        'page_ref_line_threshold': 10,
        'left_jump_ratio_threshold': 0.5,
        'num_words_min': 200,
        'num_words_max': 600,
        'inventory_threshold': 3804,
    },
    'index_page_late_print': {
        'median_line_width_min': 250,
        'median_line_width_max': 400,
        'num_words_min': 200,
        'num_words_max': 500,
        'stdev_line_width_min': 100,
        'stdev_line_width_max': 400,
        'num_lines_min': 130,
        'num_lines_max': 230,
        'num_dates_threshold': 5,
        'num_page_refs_threshold': 15,
        'inventory_threshold': 3805,
        'left_jump_ratio_min': 0.5,
    },
    'resolution_page': {
        'left_jump_ratio_max': 0.3,
        'num_words_min': 700,
        'num_words_max': 1200,
    },
    'respect_page': {
        'column_min_threshold': 3,
        'column_max_threshold': 4,
        'capitalized_word_line_ratio': 0.3,
        'capital_freq_ratio': 0.5,
    },
    'title_page': {
        'min_char_width': 40,
        'min_word_height': 60,
        'min_word_num': 10,
        'num_top_half_words': 60,
        'num_top_half_chars': 150,
        'max_line_width_threshold': 1000,
        'large_word_lines_threshold': 2,
        'title_line_top_threshold': 1300,
        'max_word_num': 500
    }
}

column_config = {
    'avg_char_width': 20,
    'word_conf_threshold': 10,
}

fuzzy_search_config = {
    "default": {
        'filter_distractors': True,
        'include_variants': True,
        'use_word_boundaries': True,
        'max_length_variance': 3,
        'levenshtein_threshold': 0.7,
        'char_match_threshold': 0.7,
        'ngram_size': 3,
        'skip_size': 1
    }
}
