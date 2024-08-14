from __future__ import annotations

import copy
from collections import defaultdict
from typing import List, Union

import pagexml.model.physical_document_model as pdm

import republic.model.republic_document_model as rdm


ACCEPTED_TYPES = {
    'PageXMLTextRegion',
    'PageXMLTextLine',
    'PageXMLColumn',
    'PageXMLPage',
    'PageXMLScan',
    'Session',
    'Resolution'
}


class StatsDoc:

    def __init__(self, doc_id: str, doc_type: str, inv_num: Union[str, int],
                 words: int, lines: int, page_stats_docs: List[StatsDoc] = None):
        self.doc_id = doc_id
        self.doc_type = doc_type
        self.inv_num = inv_num
        self.words = words
        self.lines = lines
        self.page_stats_docs = []
        if page_stats_docs is not None:
            for page_stats_doc in page_stats_docs:
                if isinstance(page_stats_doc, StatsDoc) is False:
                    raise TypeError(f"page_stats_docs must be of type StatsDoc, not {type(page_stats_doc)}")
        self.page_stats_docs = page_stats_docs if page_stats_docs is not None else []

    def __repr__(self):
        return f"{self.__class__.__name__}(\n\tdoc_id='{self.doc_id}', \n\tdoc_type='{self.doc_type}'," \
               f"inv_num='{self.inv_num}', \n\twords={self.words}, lines={self.lines}\n)"

    def to_json(self):
        json_data = {
            'doc_id': self.doc_id,
            'doc_type': self.doc_type,
            'inv_num': self.inv_num,
            'words': self.words,
            'lines': self.lines
        }
        if self.page_stats_docs:
            json_data['page_stats_docs'] = [page_stats_doc.to_json() for page_stats_doc in self.page_stats_docs]
        return json_data

    @staticmethod
    def from_json(json_data):
        page_stats_docs = None
        if 'page_stats_docs' in json_data:
            page_stats_docs = [StatsDoc.from_json(sd) for sd in json_data['page_stats_docs']]
        return StatsDoc(json_data['doc_id'], json_data['doc_type'], json_data['inv_num'],
                        json_data['words'], json_data['lines'],
                        page_stats_docs=page_stats_docs)


def make_stats_doc(doc: Union[pdm.PageXMLDoc, rdm.RepublicDoc]):
    if doc.__class__.__name__ not in ACCEPTED_TYPES:
        raise TypeError(f'doc must be one of types {ACCEPTED_TYPES}, '
                        f'not {doc.__class__.__name__}')
    else:
        doc_type = doc.__class__.__name__
    """
    if isinstance(doc, pdm.PageXMLPage):
        doc_type = 'PageXMLPage'
    elif isinstance(doc, rdm.Session):
        doc_type = 'Session'
    elif isinstance(doc, rdm.Resolution):
        doc_type = 'Resolution'
    else:
        raise TypeError(f'doc must be of type PageXMLPage, Session or Resolution, '
                        f'not {doc.__class__.__name__}')
    """
    if isinstance(doc, rdm.Session) or isinstance(doc, rdm.Resolution):
        page_stats = defaultdict(StatsDoc)
        for tr in doc.text_regions:
            if tr.metadata['page_id'] not in page_stats:
                page_stats[tr.metadata['page_id']] = StatsDoc(tr.metadata['page_id'], 'PageXMLPage',
                                                              tr.metadata['inventory_num'], tr.stats['words'],
                                                              tr.stats['lines'])
            else:
                page_stats[tr.metadata['page_id']].words += tr.stats['words']
                page_stats[tr.metadata['page_id']].lines += tr.stats['lines']
        page_stats_docs = sorted([page_stats[page_id] for page_id in page_stats], key=lambda p: p.doc_id)
    else:
        page_stats_docs = None
    stats_doc = StatsDoc(doc.id, doc_type, doc.metadata['inventory_num'],
                         doc.stats['words'], doc.stats['lines'],
                         page_stats_docs=page_stats_docs)
    return stats_doc


def merge_stats_docs(stats_docs: List[StatsDoc]) -> StatsDoc:
    """Merge multiple StatsDocs instances into a single instance."""
    if len(stats_docs) == 1:
        return copy.deepcopy(stats_docs[0])
    doc_ids = [sd.doc_id for sd in stats_docs]
    doc_types = [sd.doc_type for sd in stats_docs]
    inv_nums = [sd.inv_num for sd in stats_docs]
    page_stats_docs = [psd for sd in stats_docs for psd in sd.page_stats_docs]
    assert len(set(doc_ids)) == 1, f"trying to merge StatsDocs with multiple doc_ids {doc_ids}"
    doc_id = doc_ids[0]
    assert len(set(doc_types)) == 1, f"multiple doc_types for StatsDocs with same doc_id '{doc_id}': {set(doc_types)}"
    assert len(set(inv_nums)) == 1, f"multiple inv_nums for StatsDocs with same doc_id '{doc_id}': {set(inv_nums)}"
    total_words = sum([sd.words for sd in stats_docs])
    total_lines = sum([sd.lines for sd in stats_docs])
    merged_page_stats_docs = merge_stats_docs_list(page_stats_docs)
    return StatsDoc(doc_id, doc_types[0], inv_num=inv_nums[0],
                    words=total_words, lines=total_lines,
                    page_stats_docs=merged_page_stats_docs)


def merge_stats_docs_list(stats_docs: List[StatsDoc], debug: int = 0) -> List[StatsDoc]:
    """For a list of StatsDoc instances, merge the ones with the same doc_id and return
    the reduced list of instances."""
    has_stats_docs = defaultdict(list)
    if debug > 1:
        print('merge_stats_docs_list - received stats_docs:', stats_docs)
    for sd in stats_docs:
        if isinstance(sd, StatsDoc) is False:
            raise TypeError(f"elements of stats_docs must be of type 'StatsDoc', not '{type(sd)}'")
        has_stats_docs[sd.doc_id].append(sd)
    merged_stats_docs = []
    for doc_id in has_stats_docs:
        if debug > 1:
            print(f'merge_stats_docs_list - doc_id: {doc_id}\tnum docs: {len(has_stats_docs[doc_id])}')
        merged_stats_doc = merge_stats_docs(has_stats_docs[doc_id])
        merged_stats_docs.append(merged_stats_doc)
    return merged_stats_docs
