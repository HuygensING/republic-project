import copy
from collections import defaultdict
from typing import Dict, Generator, List, Tuple, Callable

import fuzzy_search
import pagexml.model.physical_document_model as pdm
from fuzzy_search.search.phrase_searcher import FuzzyPhraseSearcher
from pagexml.helper.pagexml_helper import make_text_region_text

import republic.model.republic_document_model as rdm
from republic.helper.metadata_helper import doc_id_to_iiif_url
from republic.helper.metadata_helper import get_majority_line_class
from republic.helper.text_helper import determine_language
from republic.model.resolution_phrase_model import proposition_opening_phrases
from republic.parser.logical.printed_resolution_parser import get_base_metadata
from republic.parser.logical.paragraph_parser import running_id_generator


def make_opening_searcher(year_start: int, year_end: int, config: dict = None, debug: int = 0):
    # print('year_start:', year_start)
    opening_phrases = [phrase for phrase in proposition_opening_phrases if
                       phrase['start_year'] < year_end and phrase['end_year'] > year_start]
    # print(opening_phrases)
    if debug > 0:
        print('number of opening phrases:', len(opening_phrases))
    if not config:
        config = {
            'levenshtein_threshold': 0.7,
            'ngram_size': 3,
            'skip_size': 1,
            'include_variants': True
        }
    return FuzzyPhraseSearcher(phrase_list=opening_phrases, config=config)


def make_paragraph_text(lines: List[pdm.PageXMLTextLine]) -> Tuple[str, List[Dict[str, any]]]:
    text, line_ranges = make_text_region_text(lines, word_break_chars='-„=')
    return text, line_ranges


def check_lines_have_boundary_signals(lines: List[pdm.PageXMLTextLine], curr_index: int,
                                      prev_line: pdm.PageXMLTextLine, debug: int = 0) -> bool:
    if debug > 1:
        print('check_lines_have_boundary_signals - curr_index:', curr_index)
    if curr_index == -1:
        curr_line = prev_line
    else:
        curr_line = lines[curr_index]
    if curr_line is None:
        return True
    if debug > 1:
        print('check_lines_have_boundary_signals - curr_line:', curr_line.metadata['line_class'], curr_line.text)
    if curr_line.metadata['line_class'].startswith('para') is False:
        if debug > 1:
            print('\tno para line:', True)
        return True
    if curr_line.text is None:
        if debug > 1:
            print('\tno text:', True)
        return True
    if len(lines) == curr_index+1:
        if debug > 1:
            print('\tno next line:', True)
        return True
    if curr_line.text and curr_line.text[-1] == '.':
        if debug > 1:
            print('\tends with period:', True)
        return True
    next_line = lines[curr_index+1]
    if debug > 1:
        print('check_lines_have_boundary_signals - next_line:', next_line.metadata['line_class'], next_line.text)
    if next_line.text is None:
        if debug > 1:
            print('\tno text:', True)
        return True
    if curr_line.text[-1] in '-„':
        if debug > 1:
            print('\tcurr line has word break:', False)
        return False
    if next_line.text[0].isalpha() and next_line.text[0].islower():
        if debug > 1:
            print('\tnext line starts with lower alpha:', False)
        return False
    if debug > 1:
        print('\telse:', True)
    return True


def get_session_paragraph_line_groups(session_trs: List[pdm.PageXMLTextRegion],
                                      debug: int = 0):
    paras = []
    para = []
    prev_line = None
    para_trs = [tr for tr in session_trs if tr.has_type('para')]
    for tr in para_trs:
        for line in tr.lines:
            line.metadata['text_region_id'] = tr.id
    attendance_trs = [tr for tr in session_trs if tr.has_type('attendance')]
    date_trs = [tr for tr in session_trs if tr.has_type('date')]
    para_lines = [line for tr in para_trs for line in tr.lines]
    for si, session_tr in enumerate(attendance_trs):
        paras.append((session_tr.metadata['text_region_class'], session_tr.lines))
    for li, line in enumerate(para_lines):
        if line.metadata['line_class'] == 'para_start':
            if check_lines_have_boundary_signals(para_lines, li-1, prev_line, debug=debug):
                if len(para) > 0:
                    if debug > 1:
                        print('reached para_start, adding previous as number', len(paras)+1)
                    paras.append(('para', para))
                para = []
        if debug > 1:
            print(f"{line.coords.top: >4}-{line.coords.bottom: <4}\t{line.metadata['line_class']: <20}\t{line.text}")
        para.append(line)
        if debug > 1:
            print(f"current paragraph has {len(para)} lines")
        if line.metadata['line_class'] == 'para_end':
            if check_lines_have_boundary_signals(para_lines, li, prev_line, debug=debug):
                if len(para) > 0:
                    if debug > 1:
                        print('reached para_end, adding current as number', len(paras)+1)
                    paras.append(('para', para))
                para = []
        prev_line = line
    if len(para) > 0:
        paras.append(('para', para))
    return paras


def make_session_paragraphs(session: rdm.Session, debug: int = 0):
    paras = get_session_paragraph_line_groups(session.text_regions, debug=debug)
    # print('make_session_paragraphs - len(paras):', len(paras))
    doc_text_offset = 0
    for pi, para in enumerate(paras):
        para_type, para_lines = para
        paragraph_id = f"{session.id}-para-{pi+1}"
        metadata = copy.deepcopy(session.metadata)
        metadata['page_ids'] = []
        metadata['scan_ids'] = []
        metadata['id'] = paragraph_id
        metadata['type'] = "paragraph"
        text_region_ids = []
        for line in para_lines:
            if line.metadata["parent_id"] not in text_region_ids:
                text_region_ids.append(line.metadata["parent_id"])
                if line.metadata['page_id'] not in metadata['page_ids']:
                    metadata['page_ids'].append(line.metadata['page_id'])
                if line.metadata['scan_id'] not in metadata['scan_ids']:
                    metadata['scan_ids'].append(line.metadata['scan_id'])
        text, line_ranges = make_paragraph_text(para_lines)
        paragraph = rdm.RepublicParagraph(lines=para_lines, metadata=metadata,
                                          text=text, line_ranges=line_ranges)
        paragraph.metadata["start_offset"] = doc_text_offset
        paragraph.metadata["para_type"] = para_type
        paragraph.add_type(para_type)
        paragraph.text_regions = get_line_grouped_text_regions(paragraph, debug=debug)
        for tr in paragraph.text_regions:
            tr.metadata['iiif_url'] = doc_id_to_iiif_url(tr.id)
        doc_text_offset += len(paragraph.text)
        yield paragraph
    return None


def get_paragraph_page_ids(paras):
    return sorted(set([page_id for para in paras for page_id in para.metadata['page_ids']]))


def get_line_grouped_text_regions(republic_doc: rdm.RepublicDoc, debug: int = 0) -> List[pdm.PageXMLTextRegion]:
    """Keep track of which text regions in the physical space correspond
    to the republic_doc content. This is potentially needed for linking
    marginalia to republic_docs."""
    tr_grouped_lines = defaultdict(list)
    metadata = defaultdict(dict)
    res_trs = []
    if isinstance(republic_doc, rdm.Resolution):
        res_trs = [tr for para in republic_doc.paragraphs for tr in para.text_regions]
        if debug > 0:
            print(f"get_line_grouped_text_regions - {republic_doc.main_type} {republic_doc.id}")
            print(f"get_line_grouped_text_regions - number of text_regions: {len(res_trs)}")
    else:
        for line in republic_doc.lines:
            if 'text_region_id' in line.metadata and line.metadata['text_region_id']:
                parent_id = line.metadata['text_region_id']
            elif 'column_id' in line.metadata and line.metadata['column_id']:
                parent_id = line.metadata['column_id']
            elif 'scan_id' in line.metadata and line.metadata['scan_id']:
                parent_id = line.metadata['scan_id']
            elif 'page_id' in line.metadata and line.metadata['page_id']:
                parent_id = line.metadata['page_id']
            else:
                raise KeyError(f"no parent id in metadata for line {line.id}")
            tr_grouped_lines[parent_id].append(line)
            for field in ['column_id', 'page_id', 'scan_id']:
                if field in line.metadata:
                    metadata[parent_id][field] = line.metadata[field]
        if debug > 0:
            print(f"get_line_grouped_text_regions - {republic_doc.main_type} {republic_doc.id}")
            print(f"get_line_grouped_text_regions - number of tr_grouped_lines: {len(tr_grouped_lines)}")
        for group_id in tr_grouped_lines:
            coords = pdm.parse_derived_coords(tr_grouped_lines[group_id])
            group_tr = pdm.PageXMLTextRegion(doc_id=group_id, coords=coords, metadata=metadata[group_id],
                                             lines=tr_grouped_lines[group_id])
            group_tr.metadata['parent_id'] = group_id
            res_trs.append(group_tr)
    return res_trs


def link_marginalia(resolution: rdm.Resolution, marg_trs: List[pdm.PageXMLTextRegion], debug: int = 0):
    if debug > 0:
        print(f"link_marginalia - resolution {resolution.id}")
    res_trs = get_line_grouped_text_regions(resolution)
    parent_field_order = ['column_id', 'page_id']
    for res_tr in res_trs:
        # print(res_tr.metadata)
        for marg_tr in marg_trs:
            same_parent = False
            # print('\t', marg_tr.metadata)
            for id_field in parent_field_order:
                if id_field in marg_tr.metadata and id_field in res_tr.metadata:
                    if marg_tr.metadata[id_field] == res_tr.metadata[id_field]:
                        same_parent = True
            if same_parent is False:
                continue
            if debug > 0:
                print(f"link_marginalia - checking overlap between resolution tr {res_tr.id} and marg_tr {marg_tr.id}")
            if pdm.is_vertically_overlapping(res_tr, marg_tr, threshold=0.5):
                if debug > 0:
                    print(f"\tregions overlap vertically, linking marginalia")
                resolution.linked_text_regions.append(marg_tr)
    return None


def prep_resolution(resolution: rdm.Resolution, marg_trs: List[pdm.PageXMLTextRegion], debug: int = 0):
    resolution.metadata['lang'] = list({para.metadata['lang'] for para in resolution.paragraphs})
    if debug > 0:
        print(f"handwritten_resolution_parser.prep_resolution - calling set_proposition_type for res {resolution.id}")
    resolution.set_proposition_type()
    resolution.metadata["page_ids"] = get_paragraph_page_ids(resolution.paragraphs)
    resolution.metadata['inventory_id'] = resolution.paragraphs[0].metadata['inventory_id']
    # resolution.linked_text_regions = get_line_grouped_text_regions(resolution, debug=debug)
    link_marginalia(resolution, marg_trs, debug=debug)
    for linked_tr in resolution.linked_text_regions:
        linked_tr.metadata['iiif_url'] = doc_id_to_iiif_url(linked_tr.id)
        if linked_tr.has_type('marginalia'):
            marginalium_text = ' '.join([line.text for line in linked_tr.lines if line.text is not None])
            resolution.add_label(marginalium_text, 'marginalia', provenance={'label_source': linked_tr.id})


def initialise_resolution(session: rdm.Session, generate_id: Callable,
                          doc_type: str,
                          opening_matches: List[fuzzy_search.PhraseMatch] = None):
    metadata = get_base_metadata(session, generate_id(), doc_type=doc_type)
    resolution = rdm.Resolution(doc_id=metadata['id'], metadata=metadata,
                                evidence=opening_matches if opening_matches is not None else [])
    resolution.add_type(doc_type)
    return resolution


def needs_followed_by_lookup(matches: List[fuzzy_search.PhraseMatch]) -> bool:
    if rdm.get_proposition_type_from_evidence(matches) not in {'onbekend', 'afhankelijk'}:
        return False
    return has_followed_by(matches)


def has_followed_by(matches: List[fuzzy_search.PhraseMatch]) -> bool:
    for match in matches:
        if 'followed_by' in match.phrase.properties:
            return True
    return False


def resolve_followed_by(followed_by_searcher: FuzzyPhraseSearcher,
                        matches: List[fuzzy_search.PhraseMatch], doc: dict[str, any]) -> List[fuzzy_search.PhraseMatch]:
    resolved_matches = [match for match in matches]
    for match in matches:
        if 'followed_by' in match.phrase.properties:
            following_matches = followed_by_searcher.find_matches(doc)
            print(f"following_matches:", following_matches)
            resolved_matches.extend(following_matches)
    return resolved_matches


def make_followed_by_searcher(opening_searcher: FuzzyPhraseSearcher) -> FuzzyPhraseSearcher:
    following_phrases = []
    phrases = opening_searcher.phrase_model.phrase_index.values()
    for phrase in phrases:
        if 'followed_by' in phrase.properties:
            following_phrases.extend(phrase.properties['followed_by'])
    followed_by_searcher = FuzzyPhraseSearcher(phrase_list=following_phrases, config=opening_searcher.config)
    return followed_by_searcher


def get_session_resolutions(session: rdm.Session,
                            opening_searcher: FuzzyPhraseSearcher,
                            debug: int = 0) -> Generator[rdm.Resolution, None, None]:
    resolution = None
    attendance_list = None
    session_offset = 0
    followed_by_searcher = make_followed_by_searcher(opening_searcher)
    generate_id = running_id_generator(session.id, '-resolution-')
    marg_trs = [tr for tr in session.text_regions if tr.has_type('marginalia')]
    if debug > 0:
        print(f"\nhandwritten_resolution_parser.get_session_resolutions - session {session.id}")
        print(f"handwritten_resolution_parser.get_session_resolutions - number of marg_trs: {len(marg_trs)}")
    ses_para_count = 0
    res_para_count = 0
    for paragraph in make_session_paragraphs(session, debug=debug):
        ses_para_count += 1
        tr_types = [get_majority_line_class(tr.lines, debug=0) for tr in paragraph.text_regions]
        # print(f"\ntr_types: {tr_types}")
        if 'attendance' in tr_types:
            paragraph.add_type('attendance')
            if attendance_list is None:
                metadata = get_base_metadata(session, session.id + '-attendance_list', 'attendance_list')
                attendance_list = rdm.AttendanceList(doc_id=metadata['id'], metadata=metadata)
            if debug > 1:
                print(f"adding paragraph {paragraph.id} to attendance_list {attendance_list.id}")
            attendance_list.add_paragraph(paragraph)
            res_para_count += 1
            session_offset += len(paragraph.text)
            continue
        if 'resolution' in tr_types:
            paragraph.add_type('resolution')
        else:
            paragraph.add_type(tr_types)
        # print(f"   paragraph has type: {paragraph.type}")
        paragraph.metadata['lang'] = determine_language(paragraph.text)
        if debug > 0:
            print('handwritten_resolution_parser.get_session_resolutions - paragraph:\n', paragraph.text[:500], '\n')
        doc = {'text': paragraph.text, 'id': paragraph.id}
        opening_matches = opening_searcher.find_matches(doc, debug=0)
        for match in opening_matches:
            if match.phrase.max_start_offset < match.offset:
                print('handwritten_resolution_parser.get_session_resolutions - offset beyond max_start_offset')
                print(f"    MATCH SHOULD NOT BE OPENING: {match}")
                match.text_id = paragraph.id
                if debug >= 0:
                    print('\t', match.offset, '\t', match.string, '\t', match.variant.phrase_string)
        if needs_followed_by_lookup(opening_matches):
            opening_matches = resolve_followed_by(followed_by_searcher, opening_matches, doc)
        if attendance_list:
            # If there is a previous attendance list, finish it, yield and reset to None
            attendance_list.metadata["page_ids"] = get_paragraph_page_ids(attendance_list.paragraphs)
            yield attendance_list
            attendance_list = None
        if len(opening_matches) > 0 and opening_matches[0].has_label('reviewed'):
            paragraph.add_type('reviewed')
            resolution = initialise_resolution(session, generate_id, doc_type='review',
                                               opening_matches=opening_matches)
            if debug > 0:
                print(f"adding paragraph {paragraph.id} to resolution {resolution.id}")
            resolution.add_paragraph(paragraph, matches=opening_matches)
            res_para_count += 1
            prep_resolution(resolution, marg_trs, debug=debug)
            yield resolution
            resolution = None
            session_offset += len(paragraph.text)
            continue
        if len(opening_matches) > 0:
            if resolution:
                prep_resolution(resolution, marg_trs, debug=debug)
                yield resolution
            resolution = initialise_resolution(session, generate_id, doc_type='resolution',
                                               opening_matches=opening_matches)
        elif paragraph.has_type('resolution') and resolution is None:
            resolution = initialise_resolution(session, generate_id, doc_type='resolution',
                                               opening_matches=opening_matches)
        if debug > 0:
            print(f'handwritten_resolution_parser.get_session_resolutions - '
                  f'session.metadata.resolution_type: {session.metadata["resolution_type"]}')
            print(f'handwritten_resolution_parser.get_session_resolutions - '
                  f'metadata.resolution_type: {resolution.metadata["resolution_type"]}')
        if resolution is not None:
            if debug > 0:
                print(f"adding paragraph {paragraph.id} to resolution {resolution.id}")
            resolution.add_paragraph(paragraph, matches=opening_matches)
            res_para_count += 1
            # resolution.evidence += opening_matches
        # print('start offset:', session_offset, '\tend offset:', session_offset + len(paragraph.text))
        session_offset += len(paragraph.text)
    if attendance_list:
        attendance_list.metadata["page_ids"] = get_paragraph_page_ids(attendance_list.paragraphs)
        yield attendance_list
    if resolution:
        prep_resolution(resolution, marg_trs, debug=debug)
        yield resolution
    if ses_para_count != res_para_count:
        print(f"handwritten_resolution_parser.get_session_resolutions: \n\t"
              f"number of session paragraphs ({ses_para_count}) not the same as "
              f"number of resolution paragraphs ({res_para_count})")
