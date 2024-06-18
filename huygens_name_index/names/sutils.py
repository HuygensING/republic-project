#!/usr/bin/env python

"""Objects common to all scripts"""

import os
import tarfile
import string
import shutil
import time

def hilite(string, ok=True, bold=False):
    """Return an highlighted version of 'string'."""
    attr = []
    if ok:  # green
        attr.append('32')
    elif ok != -1:  # red
        attr.append('31')
    if bold:
        attr.append('1')
    return '\x1b[%sm%s\x1b[0m' % (';'.join(attr), string)

try:
    import psyco;

    psyco.full()
except ImportError:
    pass


class Base(object):

    def __init__(self):
        self._skipped = 0
        self.total = 0
        self._imported = 0
        self._exited = False
        self._lowercase_names = set()
        self._skip_reasons = []
        self._started = time.time()
        if os.path.isdir('out'):
            shutil.rmtree('out')
        os.mkdir('out')

    def __del__(self):
        if not self._exited:
            self.tear_down()

    def tear_down(self):
        self._exited = True
        elapsed = "%0.3f" % (time.time() - self._started)
        hl = hilite
        print(
        "total:%s imported:%s skipped=%s in %s secs" \
        % (hl(self.total), hl(self._imported), hl(self._skipped), hl(elapsed)))
        if self._skip_reasons:
            print()
            "skip reasons:"
            for x in set(self._skip_reasons):
                print(
                "(%s) %s" % (hl(self._skip_reasons.count(x), 0), x))
        compress_output_files()

    def skip(self, reason=""):
        self._skipped += 1
        if reason:
            self._skip_reasons.append(reason)

    def name_already_processed(self, name):
        """Return True if the name of the person has already been
        processed to avoid duplicate persons.
        """
        if not name:
            return True
        lowercased_name = name.lower()
        if lowercased_name in self._lowercase_names:
            return True
        else:
            self._lowercase_names.add(lowercased_name)
            return False

    def print_progress(self, index, name=None):
        s = "processing: %s/%s" % (index, self.total)
        if name is not None:
            s += " - " + repr(name)
        print(
        s)

    def write_file(self, bdes, id, folder_name='out'):
        # index = str(index).zfill(len(str(self.total)))
        filename = os.path.join(folder_name, "%s.xml" % id)
        bdes.to_file(filename)
        self._imported += 1


def compress_output_files(output_folder='out'):
    tar = tarfile.open("%s.tar.gz" % output_folder, "w:gz")
    for name in os.listdir(output_folder):
        tar.add(output_folder + "/" + name, arcname=name)
    tar.close()


INVALID_CHARS = string.punctuation.replace('(', '')
INVALID_CHARS = INVALID_CHARS.replace(')', '')
INVALID_CHARS = INVALID_CHARS.replace('.', '')


def sanitize_name(name):
    """Sanitize a string as follows:
     - strip() it
     - remove any punctuation from the start
     - remove any punctuation from the tail
    """
    name = name.strip()
    name = name.replace('  ', ' ')
    while name[0] in INVALID_CHARS:
        name = name[1:]
    while name[-1:] in INVALID_CHARS:
        name = name[:-1]
    return name
