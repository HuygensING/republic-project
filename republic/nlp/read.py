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


def read_para_files(para_dir: str):
    return glob.glob(os.path.join(para_dir, 'resolution*.tsv.gz'))
