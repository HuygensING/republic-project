from typing import Dict
from collections import Counter
import os
import pickle


def get_word_freq_filename(period: Dict[str, any], word_freq_type: str, data_dir: str) -> str:
    filename = f'period_word_freq-{word_freq_type}-{period["period_start"]}-{period["period_end"]}.pcl'
    return os.path.join(data_dir, filename)


def write_word_freq_file(period: Dict[str, any], word_freq_type: str,
                         word_freq_counter: Counter, data_dir: str) -> None:
    period_word_freq_file = get_word_freq_filename(period, word_freq_type, data_dir)
    with open(period_word_freq_file, 'wb') as fh:
        return pickle.dump(word_freq_counter, fh)


def read_word_freq_file(period: Dict[str, any], word_freq_type: str, data_dir: str) -> Counter:
    period_word_freq_file = get_word_freq_filename(period, word_freq_type, data_dir)
    with open(period_word_freq_file, 'rb') as fh:
        return pickle.load(fh)


def read_word_freq_counter(inventory_config: dict, word_freq_type: str) -> Counter:
    period = inventory_config['spelling_period']
    return read_word_freq_file(period, word_freq_type, inventory_config['data_dir'])
