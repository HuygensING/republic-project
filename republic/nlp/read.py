import glob
import gzip
import json
import os
from collections import defaultdict
from typing import Dict, List, Tuple, Union

from dateutil.parser import parse as date_parse

from republic.helper.utils import get_project_dir


def read_tsv(fname: str, has_headers: bool = False, use_headers: str = None,
             as_json: bool = False, ignore_warnings: bool = False):
    open_func = gzip.open if fname.endswith('gz') else open
    with open_func(fname, 'rt') as fh:
        headers = None
        if has_headers is True:
            header_line = next(fh)
            headers = header_line.strip('\n').split('\t')
        for li, line in enumerate(fh):
            # process headers (if present)
            if headers is None and use_headers is None:
                raise ValueError('Cannot return as JSON when file has no headers and "use_headers" is None')
            elif headers is None:
                headers = use_headers

            # process columns
            cols = line.strip('\n').split('\t')
            if len(cols) != len(headers) and ignore_warnings is False:
                print(f"line {li + 2}:", line)
                raise IndexError(f"line {li + 2}: number of columns ({len(cols)}) is different "
                                 f"from the number of headers ({len(headers)}).")

            # check columns and headers align
            elif len(cols) > len(headers):
                proper_cols = cols[:len(headers)]
                text = proper_cols[-1]
                proper_cols[-1] = '\t'.join([text] + cols[len(headers):])
                cols = proper_cols

            # determine return type
            if as_json:
                yield {header: cols[hi] for hi, header in enumerate(headers)}
            else:
                yield cols
    return None


class ParaReader:

    def __init__(self, para_files: List[str], ignorecase: bool = False):
        self.para_files = para_files
        self.ignorecase = ignorecase

    def __iter__(self):
        for para_file in self.para_files:
            for para in read_paragraphs(para_file):
                if self.ignorecase is True:
                    para[-1] = para[-1].lower()
                yield para


def read_paragraphs(para_file: str, as_json: bool = False, has_header: bool = True,
                    headers: List[str] = None):
    with gzip.open(para_file, 'rt') as fh:
        if has_header is True:
            headers = next(fh).strip('\n').split('\t')
        if as_json is True and headers is None:
            raise ValueError(f"cannot return JSON without headers")
        for line in fh:
            cols = line.strip('\n').split('\t')
            if as_json is True:
                yield {header: cols[hi] for hi, header in enumerate(headers)}
            else:
                yield cols
    return None


def make_plain_text_file(para_files, plan_text_filename: str):
    with open(plan_text_filename, 'wt') as fh:
        for para_file in para_files:
            for _, _, _, text in read_paragraphs(para_file):
                fh.write(f'{text}\n')


def read_para_files_from_dir(para_dir: str, as_inv_dict: bool = False):
    para_files = glob.glob(os.path.join(para_dir, 'resolution*.tsv.gz'))
    if as_inv_dict:
        inv_dict = {}
        for para_file in para_files:
            inv = int(para_file.split('-')[-1][:4])
            inv_dict[inv] = para_file
        return inv_dict
    else:
        return para_files


def read_paragraphs_from_files(para_files: Union[str, List[str]]):
    if isinstance(para_files, str):
        para_files = [para_files]
    for para_file in para_files:
        for para in read_paragraphs(para_file):
            yield para
    return None


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
    period_files = {}
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
        period = inv_period[inv_num]
        if period not in period_files:
            period_files[period] = []
        period_files[period].append(res_file)
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



