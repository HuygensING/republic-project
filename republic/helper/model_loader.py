import os
import pickle

import settings
from republic.helper.paragraph_helper import LineBreakDetector
from republic.helper.utils import get_project_dir


def load_line_break_detector(model_file: str = None) -> LineBreakDetector:
    if model_file is None:
        model_file = settings.lbd_model
        project_dir = get_project_dir()
        model_file = os.path.join(project_dir, model_file)
    with open(model_file, 'rb') as fh:
        return pickle.load(fh)
