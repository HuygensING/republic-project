from typing import Dict, List
from collections import defaultdict
import re

from pagexml.model.physical_document_model import PageXMLTextLine, parse_derived_coords

from republic.model.republic_document_model import RepublicParagraph, Resolution, Session
import republic.model.republic_document_model as rdm
from republic.parser.logical.printed_session_parser import get_session_scans_version
from republic.parser.logical.printed_resolution_parser import get_session_resolutions
from republic.parser.logical.printed_resolution_parser import configure_resolution_searchers
from republic.helper.metadata_helper import make_scan_urls


def make_paragraph_line_annotations(paragraph: RepublicParagraph, doc_text_offset: int,
                                    line_index: Dict[str, PageXMLTextLine]) -> List[Dict[str, any]]:
    annotations = []
    tr_lines = defaultdict(list)
    for line_range in paragraph.line_ranges:
        line = line_index[line_range['line_id']]
        tr_lines[line.metadata['column_id']].append(line_range)
    for column_id in tr_lines:
        coords = parse_derived_coords([line_index[line_range['line_id']] for line_range in tr_lines[column_id]])
        first_line = line_index[tr_lines[column_id][0]['line_id']]
        tr_id = first_line.metadata['scan_id'] + f"-text_region-{coords.x}-{coords.y}-{coords.w}-{coords.h}"
        tr_anno = {
            'id': tr_id,
            'type': 'text_region',
            'coords': coords.points,
            'start_offset': doc_text_offset + tr_lines[column_id][0]['start'],
            'end_offset': doc_text_offset + tr_lines[column_id][-1]['end'],
            'metadata': {
                'para_id': paragraph.metadata['id'],
                'scan_id': first_line.metadata['scan_id']
            }
        }
        annotations.append(tr_anno)
        for line_range in tr_lines[column_id]:
            para_offset = line_range['start']
            para_end = line_range['end']
            # line_anno = line_index[line_range['line_id']].json
            # line_anno['type'] = 'line'
            line_anno = {
                'id': line_range['line_id'],
                'type': 'line',
                'start_offset': doc_text_offset + para_offset,
                'end_offset': doc_text_offset + para_end,
                "metadata": {
                    'text_region_id': tr_id,
                    'para_id': paragraph.metadata['id'],
                    'scan_id': line_index[line_range['line_id']].metadata['scan_id']
                },
                "coords": line_index[line_range['line_id']].coords.points
            }
            annotations.append(line_anno)
    # for line_range in paragraph.line_ranges:
    return annotations


def make_paragraph_annotation(paragraph: RepublicParagraph, doc_text_offset: int,
                              parent_id: str) -> Dict[str, any]:
    if "start_offset" in paragraph.metadata:
        start_offset = paragraph.metadata["start_offset"]
    else:
        start_offset = doc_text_offset
    return {
        'id': paragraph.id,
        'type': 'paragraph',
        'metadata': {
            'parent_id': parent_id,
            'num_lines': len(paragraph.line_ranges),
            'num_words': len(re.split(r'\W+', paragraph.text))
        },
        'start_offset': start_offset,
        'end_offset': start_offset + len(paragraph.text)
    }


def make_attendance_span_annotations(attendance_list: rdm.AttendanceList) -> List[dict]:
    annotations = []
    att_num = 0
    # print('\tadding spans')
    for span in attendance_list.attendance_spans:
        annotation = {
            "id": f"{attendance_list.id}-attendant-{att_num}",
            "type": "attendant",
            "start_offset": span["offset"],
            "end_offset": span["end"],
            "metadata": {
                "class": span["class"],
                "pattern": span["pattern"],
                "parent_id": attendance_list.id,
                "delegate_id": span["delegate_id"],
                "delegate_name": span["delegate_name"],
                "delegate_score": span["delegate_score"],
            }
        }
        annotations.append(annotation)
        att_num += 1
    # print('\t', len(annotations))
    return annotations


def make_resolution_annotation(resolution: Resolution, doc_text_offset: int, parent_id: str):
    res_type = 'attendance_list' if 'attendance_list' in resolution.type else 'resolution'
    resolution_anno = {
        'id': resolution.metadata['id'],
        'type': res_type,
        'metadata': resolution.metadata,
        'paragraphs': [],
        'start_offset': doc_text_offset
    }
    resolution_anno['metadata']['parent_id'] = parent_id
    return resolution_anno


def make_session_text_version(session: Session, resolutions: List[Resolution] = None):
    session.scan_versions = get_session_scans_version(session)
    annotations = []
    line_index = {
        line.id: line for text_region in session.text_regions for line in text_region.lines
    }
    session_text_offset = 0
    session_text = ''
    opening_searcher, verb_searcher = configure_resolution_searchers()
    if not resolutions:
        resolutions = get_session_resolutions(session, opening_searcher, verb_searcher)
    resolutions = sorted(resolutions, key=lambda x: x.paragraphs[0].metadata["start_offset"])
    for resolution in resolutions:
        # print(resolution.id, type(resolution))
        resolution_anno = make_resolution_annotation(resolution, session_text_offset,
                                                     session.metadata['id'])
        annotations.append(resolution_anno)
        for paragraph in resolution.paragraphs:
            para_annotation = make_paragraph_annotation(paragraph, session_text_offset, resolution.metadata['id'])
            annotations.append(para_annotation)
            annotations += make_paragraph_line_annotations(paragraph, session_text_offset, line_index)
            session_text_offset += len(paragraph.text)
            session_text += paragraph.text
            resolution_anno['paragraphs'].append(paragraph.metadata['id'])
        resolution_anno['end_offset'] = session_text_offset
        if isinstance(resolution, rdm.AttendanceList):
            annotations += make_attendance_span_annotations(resolution)
    annotations += get_scan_annotations(annotations, session)
    session_text_doc = {
        'metadata': session.metadata,
        'text': session_text,
        "annotations": sort_annotations(annotations)
    }
    session_text_doc['metadata']['scan_versions'] = session.scan_versions
    return session_text_doc


def get_scan_annotations(annotations: List[Dict[str, any]],
                         session: Session) -> List[Dict[str, any]]:
    scan_annotations = []
    line_annotations = [anno for anno in annotations if anno['type'] == 'line']
    scan_lines = defaultdict(list)
    for line_anno in line_annotations:
        scan_lines[line_anno['metadata']['scan_id']].append(line_anno)
    for scan_id in scan_lines:
        urls = make_scan_urls(inventory_num=session.metadata['inventory_num'], scan_id=scan_id)
        scan_anno = {
            'id': scan_id,
            'type': 'scan',
            'start_offset': scan_lines[scan_id][0]['start_offset'],
            'end_offset': scan_lines[scan_id][-1]['end_offset'],
            'metadata': {
                'iiif_info_url': urls['iiif_info_url'],
                'iiif_url': urls['iiif_url'],
                'filepath': urls['jpg_filepath']
            }
        }
        scan_annotations.append(scan_anno)
    return scan_annotations


def sort_annotations(annotations: List[Dict[str, any]]) -> List[Dict[str, any]]:
    order = {
        "scan": 0,
        "attendance_list": 1,
        "resolution": 1,
        "paragraph": 2,
        "text_region": 3,
        "line": 4,
        "attendant": 5,
        "proposition_type": 6,
        "proposer_role": 7,
        "Proposer_location": 8
    }
    return sorted(annotations, key=lambda x: (x["start_offset"], order[x["type"]]))
