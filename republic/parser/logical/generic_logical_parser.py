import copy
from typing import List

import pagexml.model.physical_document_model as pdm


def copy_line(line: pdm.PageXMLTextLine, reference_parent: bool = False) -> pdm.PageXMLTextLine:
    """Copy elements of a line to a new instance without copying its parent."""
    new_line = pdm.PageXMLTextLine(doc_id=line.id, metadata=copy.deepcopy(line.metadata),
                                   coords=copy.deepcopy(line.coords), baseline=copy.deepcopy(line.baseline),
                                   xheight=line.xheight, conf=line.conf, text=line.text)
    if reference_parent:
        new_line.parent = line.parent
    return new_line


def copy_lines(lines: List[pdm.PageXMLTextLine],
               reference_parent: bool = False) -> List[pdm.PageXMLTextLine]:
    return [copy_line(line, reference_parent=reference_parent) for line in lines]