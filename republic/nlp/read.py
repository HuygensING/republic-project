import glob
import gzip
import json
import os
from collections import defaultdict
from typing import Dict, List, Tuple

from dateutil.parser import parse as date_parse

from republic.helper.utils import get_project_dir


class ParaReader:

    def __init__(self, para_files: List[str], ignorecase: bool = False):
        self.para_files = para_files
        self.ignorecase = ignorecase

    def __iter__(self):
        for para_file in self.para_files:
            for para in read_paragraphs(para_file):
                yield para


def read_paragraphs(para_file: str):
    with gzip.open(para_file, 'rt') as fh:
        for line in fh:
            yield line.strip('\n').split('\t')
    return None


def make_plain_text_file(para_files, plan_text_filename: str):
    with open(plan_text_filename, 'wt') as fh:
        for para_file in para_files:
            for _, _, _, text in read_paragraphs(para_file):
                fh.write(f'{text}\n')


def read_para_files(para_dir: str, as_inv_dict: bool = False):
    para_files = glob.glob(os.path.join(para_dir, 'resolution*.tsv.gz'))
    if as_inv_dict:
        inv_dict = {}
        for para_file in para_files:
            inv = int(para_file.split('-')[-1][:4])
            inv_dict[inv] = para_file
        return inv_dict
    else:
        return para_files


def read_metadata():
    project_dir = get_project_dir()
    inv_meta_file = os.path.join(project_dir, 'data/inventories/inventory_metadata.json')
    with open(inv_meta_file, 'rt') as fh:
        inv_meta_list = json.load(fh)
    for inv_metadata in inv_meta_list:
        try:
            if isinstance(inv_metadata['period_start'], str):
                inv_metadata['period_start'] = date_parse(inv_metadata['period_start']).date()
            if isinstance(inv_metadata['period_end'], str):
                inv_metadata['period_end'] = date_parse(inv_metadata['period_end']).date()
        except ValueError:
            print(inv_metadata)
            raise
    return inv_meta_list


def get_period_files(res_dir: str, periods: List[Tuple[int, int]] = None,
                     inv_period: Dict[int, Tuple[int, int]] = None):
    period_files = defaultdict(list)
    if inv_period is None:
        if periods is None:
            raise ValueError('must pass either periods or inv_period')
        inv_period = get_period_invs(periods)

    res_files = glob.glob(os.path.join(res_dir, 'resolution-paragraphs-Loghi*.tsv.gz'))
    for res_file in res_files:
        inv_num = int(res_file.split('-')[-1].replace('.tsv.gz', ''))
        if inv_num not in inv_period:
            continue
        if inv_num in range(3244, 3286):
            # print('skipping double from second series', inv_num)
            continue
        start, end = inv_period[inv_num]
        period_files[f"{start}-{end}"].append(res_file)
    return period_files


def get_fixed_length_periods(period_length: int, start: int, end: int, slide_step: int = None):
    if slide_step is None:
        slide_step = period_length
    return [(start, start + period_length) for start in range(start, end + 1, slide_step)]


def get_period_invs(periods: List[Tuple[int, int]]):
    inv_meta_list = read_metadata()
    # period_invs = {period: [] for period in periods}
    inv_period = {}
    for inv_metadata in inv_meta_list:
        for start, end in periods:
            if inv_metadata['year_start'] >= start and inv_metadata['year_end'] < end:
                # period_invs[(start, end)].append(inv_metadata['inventory_num'])
                inv_period[inv_metadata['inventory_num']] = (start, end)
    # return period_invs, inv_period
    return inv_period



