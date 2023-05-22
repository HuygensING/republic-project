from typing import Dict, List, Set, Tuple
import re
import copy
import datetime
from collections import defaultdict
from elasticsearch import Elasticsearch

from fuzzy_search.fuzzy_match import PhraseMatch
from pagexml.model.physical_document_model import parse_derived_coords

import republic.elastic.republic_retrieving as rep_es
import republic.model.resolution_phrase_model as rpm
from republic.helper.annotation_helper import make_match_hash_id
from republic.model.republic_document_model import RepublicParagraph, Resolution, RepublicDoc

MINIMUM_RESOLUTION_LENGTH = 150


def get_max_offset():
    opening_formulas = copy.deepcopy(rpm.proposition_opening_phrases)
    max_offset = {}
    for formula in opening_formulas:
        if 'max_offset' not in formula:
            print(formula)
            max_offset[formula['phrase']] = 10000
        else:
            max_offset[formula['phrase']] = formula['max_offset']
    variable_start_formulas = {formula['phrase'] for formula in rpm.proposition_opening_phrases
                               if formula['max_offset'] > 10}
    return variable_start_formulas, max_offset


def get_next_date(year):
    meeting_date = datetime.date(year, 1, 1)
    while meeting_date.year == year:
        yield meeting_date
        meeting_date = meeting_date + datetime.timedelta(days=1)


def map_paragraphs_to_resolutions(resolutions: List[Resolution]) -> Dict[str, Resolution]:
    paragraph_resolution_map: Dict[str, Resolution] = {}
    for resolution in resolutions:
        for para in resolution.paragraphs:
            paragraph_resolution_map[para.metadata['id']] = resolution
    return paragraph_resolution_map


def group_phrase_matches_by_resolution(phrase_matches: List[PhraseMatch],
                                       paragraph_resolution_map: Dict[str, Resolution]) -> \
        Dict[str, List[PhraseMatch]]:
    resolution_matches = defaultdict(list)
    for pm in sorted(phrase_matches, key=lambda x: (x.text_id, x.offset)):
        resolution = paragraph_resolution_map[pm.text_id]
        resolution_matches[resolution.metadata['id']].append(pm)
    return resolution_matches


def should_split(phrase_match: PhraseMatch, paragraph: RepublicParagraph, max_offset: Dict[str, int]) -> bool:
    # determine the offset of the phrase match from the line where the paragraph is to be split
    split_line_offset = get_split_line_offset(paragraph, phrase_match)
    if split_line_offset > max_offset[phrase_match.phrase.phrase_string]:
        # if the phrase match offset after the split is beyond the max offset, this should not be a split
        return False
    if phrase_match.offset > max_offset[phrase_match.phrase.phrase_string]:
        return True
    # elif phrase_match.text_id != resolution.paragraphs[0].metadata['id']:
    elif paragraph.metadata['paragraph_index'] > 0:
        return True
    return False


def get_split_texts(split: Dict[str, any], new_paragraph_offset: int) -> Tuple[str, str]:
    pre_text = split['paragraph'].text[:new_paragraph_offset]
    post_text = split['paragraph'].text[new_paragraph_offset:]
    return pre_text, post_text


def get_paragraph_splits(paragraph: RepublicParagraph, paragraph_phrase_matches: List[PhraseMatch],
                         paragraph_resolution_map: Dict[str, Resolution], max_offset: Dict[str, int],
                         variable_start_formulas: Set[str]) -> List[Dict[str, any]]:
    splits = []
    for phrase_match in sorted(paragraph_phrase_matches, key=lambda x: x.offset):
        # print(paragraph.metadata)
        # print(res_id, pm.text_id, pm.offset, pm.has_label('proposition_opening'))
        if not phrase_match.has_label('proposition_opening'):
            continue
        if paragraph.metadata['paragraph_index'] == 0 and phrase_match.offset < MINIMUM_RESOLUTION_LENGTH:
            continue
        resolution = paragraph_resolution_map[phrase_match.text_id]
        if should_split(phrase_match, paragraph, max_offset):
            # print('should split resolution:', resolution.metadata['id'], len(resolution.columns))
            if phrase_match.phrase.phrase_string in variable_start_formulas:
                # skip for now
                # TO DO: figure out how to deal with variable start formulas
                continue
                # print(paragraph.metadata['id'])
                # print(paragraph.text)
                # print('\t', phrase_match.phrase.phrase_string)
                # raise ValueError('formula is not the start of the resolution')
            else:
                split = {'phrase_match': phrase_match, 'paragraph': paragraph, 'resolution': resolution}
                # print('adding split at offset', phrase_match.offset,
                #       '\tparagraph index:', paragraph.metadata['paragraph_index'])
                splits.append(split)
    overlap = True
    while overlap:
        if len(splits) <= 1:
            break
        keep_splits = [splits[0]]
        # print('keep_splits:', keep_splits[0]['phrase_match'])
        for ci, curr_split in enumerate(splits[1:]):
            if keep_splits[-1]['phrase_match'].end < curr_split['phrase_match'].offset:
                # print('adding split:', curr_split['phrase_match'])
                keep_splits.append(curr_split)
        if len(keep_splits) == len(splits):
            # print('overlap removed')
            # print([split['phrase_match'] for split in keep_splits])
            overlap = False
        splits = keep_splits
    return splits


def get_split_line_offset(paragraph: RepublicParagraph, phrase_match: PhraseMatch) -> int:
    for line_range in paragraph.line_ranges:
        if line_range['end'] <= phrase_match.offset:
            continue
        else:
            return phrase_match.offset - line_range['start']
    return -1


def get_split_line_ranges(split: Dict[str, any]) -> Tuple[List[dict], List[dict]]:
    pre_ranges: List[Dict[str, any]] = []
    post_ranges: List[Dict[str, any]] = []
    # print("process_paragraph_splits - paragraph__id:", split['paragraph'])
    for line_range in split['paragraph'].line_ranges:
        if line_range['end'] <= split['phrase_match'].offset:
            pre_ranges.append(copy.deepcopy(line_range))
        else:
            post_ranges.append(copy.deepcopy(line_range))
    return pre_ranges, post_ranges


def get_split_matches(split: Dict[str, any],
                      paragraph_matches: List[PhraseMatch]) -> Tuple[List[PhraseMatch], List[PhraseMatch]]:
    # print(paragraph_matches)
    match_index = paragraph_matches.index(split['phrase_match'])
    pre_matches = copy.deepcopy(paragraph_matches[:match_index])
    post_matches = copy.deepcopy(paragraph_matches[match_index:])
    return pre_matches, post_matches


def get_split_columns(split: Dict[str, any], first_paragraph_num_lines: int) -> Tuple[List[dict], List[dict]]:
    line_count = 0
    first_columns, next_columns = [], []
    for column in split['resolution'].columns:
        if column['metadata']['id'] not in split['paragraph'].column_ids:
            continue
        column = copy.deepcopy(column)
        first_trs, next_trs = [], []
        for tr in column['textregions']:
            first_lines, next_lines = [], []
            for line in tr['lines']:
                line_count += 1
                if line_count <= first_paragraph_num_lines:
                    first_lines.append(line)
                else:
                    next_lines.append(line)
            if len(next_lines) == 0:
                first_trs.append(tr)
            elif len(first_lines) == 0:
                next_trs.append(tr)
            else:
                first_tr = tr
                next_tr = copy.deepcopy(tr)
                first_tr['lines'] = first_lines
                next_tr['lines'] = next_lines
                first_tr['coords'] = parse_derived_coords(first_lines)
                next_tr['coords'] = parse_derived_coords(next_lines)
                first_trs.append(first_tr)
                next_trs.append(next_tr)
        if len(next_trs) == 0:
            first_columns.append(column)
        elif len(first_trs) == 0:
            next_columns.append(column)
        else:
            first_column = column
            next_column = copy.deepcopy(column)
            first_column['textregions'] = first_trs
            next_column['textregions'] = next_trs
            first_column['coords'] = parse_derived_coords(first_trs)
            next_column['coords'] = parse_derived_coords(next_trs)
            first_columns.append(first_column)
            next_columns.append(next_column)
    return first_columns, next_columns


def get_running_id(doc: RepublicDoc) -> int:
    return int(doc.metadata['id'].split('-')[-1])


def update_running_id(para_id: str, increment: int) -> str:
    if increment == 0:
        return para_id
    id_parts = para_id.split('-')
    doc_type = id_parts[-2]
    running_number = int(id_parts[-1])
    new_number = running_number + increment
    return para_id.split(f'-{doc_type}-')[0] + f'-{doc_type}-{new_number}'


def split_paragraph(split: Dict[str, any], paragraph_id: str,
                    paragraph_increment: int) -> Tuple[RepublicParagraph, RepublicParagraph]:
    # split line ranges
    # print("split_paragraph - paragraph__id:", paragraph_id)
    first_ranges, next_ranges = get_split_line_ranges(split)
    # determine offset of new paragraph within original paragraph
    # print('split:', split['phrase_match'], split['phrase_match'].text_id, split['phrase_match'].offset)
    try:
        next_para_offset = next_ranges[0]['start']
    except IndexError:
        print(len(split['paragraph'].line_ranges))
        print(split['paragraph'].line_ranges[-1])
        print('split:', split['phrase_match'], split['phrase_match'].text_id, split['phrase_match'].offset)
        print('resolution:', split['resolution'].metadata['id'])
        print('resolution paras:', [para.metadata['id'] for para in split['resolution'].paragraphs])
        raise
    # print('first_ranges:', first_ranges)
    # print('next_ranges:', next_ranges)
    # determine next paragraph id using running number increment
    next_para_id = update_running_id(paragraph_id, paragraph_increment)
    # print('split offset:', next_para_offset)
    # split paragraph text into first paragraph and next paragraph
    first_para_text, next_para_text = get_split_texts(split, next_para_offset)
    # print('first_para_text:', first_para_text)
    # print('next_para_id:', next_para_id)
    # print('next_para_text:', next_para_text)
    # split the phrase matches of the original paragraph into those for first and next paragraph
    # first_matches, next_matches = get_split_matches(split, paragraph_matches[paragraph_id])
    # print('first_matches:', first_matches)
    # print('next_matches:', next_matches)
    # print('para_offset_decrement:', para_offset_decrement)
    first_columns, next_columns = get_split_columns(split, len(first_ranges))
    # print('first_para_column:', first_columns[0]['metadata'])
    # print('next_para_column:', next_columns[0]['metadata'])
    first_para = RepublicParagraph(metadata=split['paragraph'].metadata, columns=first_columns,
                                   text=first_para_text, line_ranges=first_ranges)
    next_para = RepublicParagraph(metadata=split['paragraph'].metadata, columns=next_columns,
                                  text=next_para_text, line_ranges=next_ranges)
    next_para.metadata['id'] = next_para_id
    # print('next paragraph id:', next_para_id)
    return first_para, next_para


def process_paragraph_splits(paragraph_splits: List[Dict[str, any]], paragraph_id: str,
                             paragraph_increment: int, max_offset: Dict[str, int]) -> List[RepublicParagraph]:
    first_para = paragraph_splits[0]['paragraph']
    split_paras = []
    # Update the id for the first part of the split paragraph, using the increment
    # caused by splits of previous paragraphs
    first_para.metadata['id'] = update_running_id(paragraph_id, paragraph_increment)
    # print("process_paragraph_splits - paragraph__id:", paragraph_id)
    for si, split in enumerate(paragraph_splits[::-1]):
        # print('number of line_ranges:', len(first_para.line_ranges))
        split['paragraph'] = first_para
        para_increment = paragraph_increment + paragraph_splits.index(split) + 1
        first_para, next_para = split_paragraph(split, paragraph_id, para_increment)
        evidence_match: PhraseMatch = copy.deepcopy(split['phrase_match'])
        if evidence_match.offset < len(first_para.text):
            print(evidence_match.json)
            print(evidence_match.text_id)
            print(first_para.metadata)
            raise ValueError('match offset is smaller than split offset')
        evidence_match.offset = evidence_match.offset - len(first_para.text)
        # print('max _offset - ', evidence_match.phrase.phrase_string, max_offset[evidence_match.phrase.phrase_string])
        if evidence_match.offset <= max_offset[evidence_match.phrase.phrase_string]:
            # print('No rollback - offset after split is within max offset')
            # print(split['phrase_match'].text_id, split['phrase_match'].offset, evidence_match.offset)
            evidence_match.text_id = next_para.metadata['id']
            next_para.evidence = evidence_match
            split_paras = [next_para] + split_paras
        else:
            # print('Rollback - offset after split is beyond max offset')
            # print(split['phrase_match'].text_id, split['phrase_match'].offset, evidence_match.offset)
            # rollback first to before split
            first_para = split['paragraph']
        # print(split['phrase_match'].offset, evidence_match.offset)
    return [first_para] + split_paras


def process_paragraphs(paragraphs: List[RepublicParagraph], paragraph_matches: Dict[str, List[PhraseMatch]],
                       paragraph_resolution_map: Dict[str, Resolution],
                       max_offset: Dict[str, int], variable_start_formulas: Set[str],
                       resolution_increment: int):
    paragraph_increment = resolution_increment
    para_group = []
    para_groups = []
    remove_matches: List[PhraseMatch] = []
    for paragraph in paragraphs:
        para = copy.deepcopy(paragraph)
        para_id = para.metadata['id']
        # print('process_paragraphs para_id:', para_id, 'line_ranges:', len(para.line_ranges))
        # print('process_paragraphs paragraph_matches:', paragraph_matches[para_id])
        para_splits = get_paragraph_splits(para, paragraph_matches[para_id],
                                           paragraph_resolution_map, max_offset, variable_start_formulas)
        resolution_increment += len(para_splits)
        if len(para_splits) == 0:
            para.metadata['id'] = update_running_id(para.metadata['id'], paragraph_increment)
            para.evidence = []
            for match in paragraph_matches[para_id]:
                new_match = copy.deepcopy(match)
                new_match.text_id = para.metadata['id']
                para.evidence.append(new_match)
            remove_matches += paragraph_matches[para_id]
            para_group.append(para)
            continue
        # print('NUMBER OF PARAGRAPH SPLITS:', len(para_splits))
        # print('process_paragraphs calling process_paragraph_splits para_id:', para_id)
        # print('process_paragraphs para_id:', para_id, 'line_ranges:', len(para.line_ranges))
        split_paras = process_paragraph_splits(para_splits, para_id,
                                               paragraph_increment, max_offset)
        for split_para in split_paras[:-1]:
            para_group.append(split_para)
            para_groups.append(para_group)
            para_group = []
        para_group.append(split_paras[-1])
        paragraph_increment += len(para_splits)
        remove_matches += [split['phrase_match'] for split in para_splits]
        # print('NUMBER OF SPLIT MATCHES:', len(split_matches))
    para_groups.append(para_group)
    return para_groups, remove_matches


def make_mappings(resolutions: List[Resolution], phrase_matches: List[PhraseMatch]):
    # make mappings for quick lookup
    res_map: Dict[str, Resolution] = {resolution.metadata['id']: resolution for resolution in resolutions}
    para_map: Dict[str: RepublicParagraph] = {paragraph.metadata['id']: paragraph for resolution in resolutions
                                              for paragraph in resolution.paragraphs}
    para_res_map = map_paragraphs_to_resolutions(resolutions)
    resolution_matches = group_phrase_matches_by_resolution(phrase_matches, para_res_map)
    para_matches: Dict[str, List[PhraseMatch]] = defaultdict(list)
    for pm in phrase_matches:
        para_matches[pm.text_id].append(pm)
    return para_map, para_res_map, res_map, para_matches, resolution_matches


def reconstruct_columns(resolution: Resolution) -> List[Dict[str, any]]:
    line_ids = []
    new_columns: List[Dict[str, any]] = []
    for para in resolution.paragraphs:
        for line_range in para.line_ranges:
            line_ids.append(line_range['line_id'])
    for column in resolution.columns:
        new_column = copy.deepcopy(column)
        for tr in new_column['textregions']:
            new_lines = [line for line in tr['lines'] if line['metadata']['id'] in line_ids]
            tr['lines'] = new_lines
            tr['coords'] = parse_derived_coords(new_lines)
        new_column['textregions'] = [tr for tr in new_column['textregions'] if len(tr['lines']) > 0]
        new_column['coords'] = parse_derived_coords(new_column['textregions'])
        if len(new_column['textregions']) > 0:
            new_columns.append(new_column)
    return new_columns


def update_metadata(resolution: Resolution) -> Dict[str, any]:
    metadata = resolution.metadata
    metadata['num_columns'] = len(resolution.columns)
    metadata['num_lines'] = len([line for col in resolution.columns for tr in col['textregions']
                                 for line in tr['lines']])

    for label in resolution.evidence[0].label_list():
        if 'proposition_type' in label:
            metadata['proposition_type'] = label.replace('proposition_type:', '')
    words = []
    for pi, para in enumerate(resolution.paragraphs):
        para.metadata['paragraph_index'] = pi
        if 'num_lines' in para.metadata:
            del para.metadata['num_lines']
        if 'num_columns' in para.metadata:
            del para.metadata['num_columns']
        words += [word for word in re.split(r'\W+', para.text) if word != '']
    metadata['num_words'] = len(words)
    return metadata


def do_paragraph_splitting(es: Elasticsearch, session_id: str, config: dict):
    resolutions = rep_es.retrieve_session_resolutions(es, session_id, config)
    phrase_matches = rep_es.retrieve_meeting_phrase_matches(es, resolutions, config)
    para_map, para_res_map, res_map, para_matches, resolution_matches = make_mappings(resolutions, phrase_matches)
    print('\tnum resolutions:', len(resolutions), '\tnum paragraphs:', len(para_map.keys()),
          '\tnum phrase matches:', len(phrase_matches))
    variable_start_formulas, max_offset = get_max_offset()
    resolution_increment = 0
    new_resolutions = []
    remove_matches = []
    add_matches = []
    sorted_resolutions = sorted(resolutions, key=lambda x: int(x.metadata['id'].split('-resolution-')[1]))
    update_from = -1

    # print([res.metadata['id'] for res in sorted_resolutions])

    for ri, resolution in enumerate(sorted_resolutions):
        res = copy.deepcopy(resolution)
        # shift this resolution's ID by the increment caused by preceding splits
        # print('checking paragraphs for resolution', res.metadata['id'], '\tparagraphs:', len(res.paragraphs),
        #       '\tphrase matches:', len(resolution_matches[res.metadata['id']]))
        # for pm in resolution_matches[resolution.metadata['id']]:
        #     print('\t', pm.text_id, pm.offset, pm.string, pm.levenshtein_similarity)
        res.metadata['id'] = update_running_id(res.metadata['id'], resolution_increment)
        paragraphs = res.paragraphs
        res.paragraphs = []
        # hack to correct paragraph index that I forgot to update earlier
        for pi, para in enumerate(paragraphs):
            para.metadata['paragraph_index'] = pi
        # print([p.metadata['id'] for p in paragraphs])
        para_groups, split_matches = process_paragraphs(paragraphs, para_matches, para_res_map,
                                                        max_offset, variable_start_formulas,
                                                        resolution_increment)
        resolution_increment += len(para_groups) - 1
        if len(para_groups) == 1:
            # print('\tno splitting needed')
            res.paragraphs = para_groups[0]
            # print('\nbefore:', len(res.evidence))
            if paragraphs[0].metadata['id'] != res.paragraphs[0].metadata['id']:
                shift = get_running_id(res.paragraphs[0]) - get_running_id(paragraphs[0])
                for pm in res.evidence:
                    pm.text_id = update_running_id(pm.text_id, shift)
            # print(res.evidence)
            # res.evidence = [pm for para in para_groups[0] for pm in para.evidence]
            # print('after:', len(res.evidence), '\n')
            new_resolutions.append(res)
        else:
            # print('SPLITTING')
            if update_from == -1:
                update_from = ri
            remove_matches += split_matches
            # print('NUMBER OF REMOVE MATCHES:', len(remove_matches))
            for pi, para_group in enumerate(para_groups):
                new_res = copy.deepcopy(res)
                new_res.metadata['id'] = update_running_id(res.metadata['id'], pi)
                new_res.paragraphs = para_group
                new_res.columns = reconstruct_columns(new_res)
                new_res.metadata = update_metadata(new_res)
                if pi > 0:
                    new_res.evidence = [para_group[0].evidence]
                    add_matches.append(para_group[0].evidence)
                new_resolutions.append(new_res)
    for res in new_resolutions:
        res.columns = reconstruct_columns(res)
        res.metadata = update_metadata(res)
    print('\tnum updated resolutions:', len(new_resolutions))
    for pm in phrase_matches:
        if pm not in remove_matches:
            remove_matches.append(pm)
    return {
        'resolutions': new_resolutions, 'update_from': update_from,
        'remove_matches': remove_matches, 'add_matches': add_matches
    }


def validate_split(es: Elasticsearch, resolution_updates: Dict[str, any], config: dict) -> None:
    prev_res_num = 0
    prev_para_num = None
    for res in resolution_updates['resolutions']:
        res_num = int(res.metadata['id'].split('resolution-')[1])
        if res_num != prev_res_num + 1:
            raise ValueError(f'invalid sequence of resolution numbers: prev num {prev_res_num}, curr num: {res_num}')
        prev_res_num = res_num
        for para in res.paragraphs:
            para_num = int(para.metadata['id'].split('-para-')[1])
            if prev_para_num is None:
                pass
            elif para_num != prev_para_num + 1:
                raise ValueError(f'invalid sequence of paragraph numbers: prev num {prev_para_num}, curr num: {para_num}')
            prev_para_num = para_num
    for match in resolution_updates['remove_matches']:
        match_id = make_match_hash_id(match)
        if not es.exists(index=config['phrase_match_index'], id=match_id):
            message = f'unknown phrase match id {match_id} (text id: {match.text_id}, phrase match cannot be removed'
            raise ValueError(message)
    return None

