import pickle

import settings
from republic.helper.paragraph_helper import LineBreakDetector


def load_line_break_detector(model_file: str = None) -> LineBreakDetector:
    if model_file is None:
        model_file = settings.lbd_model
    with open(model_file, 'rb') as fh:
        return pickle.load(fh)
