import re

import numpy as np


def has_comma_refs(text):
    return get_comma_refs_string(text) is not None


def get_comma_refs_string_type(text):
    if re.search(r'[,\.] \d+', text):
        return 'comma_digit_refs'
    elif ' siet ' in text:
        return 'redirect'
    elif re.search(r'[,\.] \w+\d+', text):
        return 'comma_alpha_digit_refs'
    elif re.search(r'[a-z] \w+\d+', text):
        return 'word_digit_refs'
    elif re.search(r'letter [A-Z]', text):
        return 'redirect'
    elif text[-1] == '-':
        return 'missing_end'
    else:
        return 'unknown'


def get_comma_refs_string(text):
    if re.search(r'[,\.] \d+', text):
        return re.sub(r'.*?[,\.] (\d+)', r'\1', text)
    elif re.search(r'[,\.] \w+\d+', text):
        return re.sub(r'.*?[,\.] (\w+\d+)', r'\1', text)
    elif re.search(r'[a-z] \w+\d+', text):
        return re.sub(r'.*?[a-z] (\w+\d+)', r'\1', text)
    else:
        return np.nan
