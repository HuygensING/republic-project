import glob
import gzip
import os
from typing import List


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
