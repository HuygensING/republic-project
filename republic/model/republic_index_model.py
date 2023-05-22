from typing import Dict, List, Union

import pagexml.model.physical_document_model as pdm


class IndexReference:

    def __init__(self, lemma: str, description: str = None,
                 page_reference: int = None, logical_reference: str = None):
        self.lemma = lemma
        self.description = description
        self.page_reference = page_reference
        self.logical_reference = logical_reference


class IndexLemma(pdm.LogicalStructureDoc):

    def __init__(self, doc_id: str = None, doc_type: Union[str,List[str]] = None, lemma_term: str = None,
                 references: List[IndexReference] = None,
                 lines: List[pdm.PageXMLTextLine] = None, text_regions: List[pdm.PageXMLTextRegion] = None):
        super().__init__(doc_id=doc_id, doc_type="index_lemma", lines=lines, text_regions=text_regions)
        if doc_type:
            self.add_type(doc_type)
        self.lemma_term: str = lemma_term
        self.references: List[IndexReference] = references
        self.page_reference: Dict[int, IndexReference] = {}
        self.logical_reference: Dict[str, IndexReference] = {}
        self.lines: List[pdm.PageXMLTextLine] = lines if lines else []
        self.text_regions: List[pdm.PageXMLTextRegion] = text_regions if text_regions else []
        # TODO: extract all page references and descriptions
        self.index_references()

    def index_references(self):
        for reference in self.references:
            if reference.page_reference:
                self.page_reference[reference.page_reference] = reference
            if reference.logical_reference:
                self.logical_reference[reference.logical_reference] = reference

    @property
    def json(self):
        json_data = super().json
        json_data['lemma'] = self.lemma_term
        json_data['references'] = self.references
        return json_data


def extract_lemma_term(lemma_lines: List[pdm.PageXMLTextLine]) -> Union[str, None]:
    """Extract the lemmata from an index entry."""
    # naive for now
    if not lemma_lines[0].has_type('lemma'):
        return ''
    else:
        lemma_term = ','.join(lemma_lines[0].text.split(',')[:-1])
        return lemma_term


def make_index_lemma_from_lines(lemma_lines: List[pdm.PageXMLTextLine]) -> IndexLemma:
    """Turn a list of categorised index lines into an IndexLemma object."""
    lemma_term = extract_lemma_term(lemma_lines)
    return IndexLemma(lemma_term=lemma_term, lines=lemma_lines)
