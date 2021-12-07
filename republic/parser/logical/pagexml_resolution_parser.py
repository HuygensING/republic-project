from typing import Dict, Generator, List, Union
from collections import Counter

from fuzzy_search.fuzzy_phrase_searcher import FuzzyPhraseSearcher, PhraseModel

import republic.model.resolution_phrase_model as rpm
import republic.model.republic_document_model as rdm
import republic.model.physical_document_model as pdm
import republic.helper.pagexml_helper as pagexml


def same_column(line1: dict, line2: dict) -> bool:
    return line1['page_num'] == line2['page_num'] and line1['column_index'] == line2['column_index']


def get_neighbour_lines(curr_line: dict, meeting_lines: List[dict], neighbour_size: int = 4) -> List[dict]:
    line_index = meeting_lines.index(curr_line)
    start_index = line_index - neighbour_size
    end_index = line_index + neighbour_size + 1
    neighbour_lines = []
    if start_index < 0:
        start_index = 0
    if end_index > len(meeting_lines):
        end_index = len(meeting_lines)
    for line in meeting_lines[start_index:end_index]:
        if line == curr_line:
            continue
        if line['coords']['left'] > curr_line['coords']['left'] + 100:
            continue
        if line['text'] and same_column(curr_line, line):
            neighbour_lines += [line]
    return neighbour_lines


def is_paragraph_start(line: dict, meeting_lines: List[dict], neighbour_size: int = 3) -> bool:
    line_index = meeting_lines.index(line)
    if not line['text'] or len(line['text']) == 0:
        # start of paragraph always has text
        return False
    if line_index > 0:
        prev_line = meeting_lines[line_index - 1]
        if line['coords']['bottom'] > prev_line['coords']['bottom'] + 60:
            # for print editions after 1705, new paragraphs
            # start with some vertical whitespace
            return True
    neighbour_lines = get_neighbour_lines(line, meeting_lines, neighbour_size=neighbour_size)
    lefts = [line['coords']['left'] for line in neighbour_lines]
    if len(lefts) == 0:
        # no surrounding text lines so this is no paragraph start
        return False
    else:
        min_left = min(lefts)
        max_left = max(lefts)
        avg_left = sum(lefts) / len(lefts)
    if line['coords']['left'] > avg_left + 100:
        # large indentation signals it's probably an incorrect line
        # from bleed through of opposite side of the page
        return False
    if max_left - min_left > 20:
        # if the surrounding lines include indentation, something else
        # is going on.
        is_start = False
    elif line['coords']['left'] > avg_left + 20:
        # this line is normally indented compared its surrounding lines
        # so probably the start of a new paragraph
        is_start = True
    else:
        # no indentation, so line is part of current paragraph
        is_start = False
    return is_start


def find_paragraph_starts(meeting: dict) -> iter:
    for line in meeting['meeting_lines']:
        if is_paragraph_start(line, meeting['meeting_lines'], neighbour_size=3):
            yield line


def find_resolution_starts(meeting: dict, resolution_searcher: FuzzyPhraseSearcher) -> iter:
    meeting_lines = meeting['meeting_lines']
    for li, line in enumerate(meeting['meeting_lines']):
        if is_paragraph_start(line, meeting_lines):
            opening_matches = resolution_searcher.find_candidates(line['text'], use_word_boundaries=False)
            if len(opening_matches) > 0:
                yield line


def make_resolution_text(meeting: dict, resolution_searcher: FuzzyPhraseSearcher) -> iter:
    text = ''
    for line in meeting['meeting_lines']:
        if not line['text']:
            continue
        if is_paragraph_start(line, meeting['meeting_lines']):
            opening_matches = resolution_searcher.find_candidates(line['text'], use_word_boundaries=False)
            if len(opening_matches) > 0:
                yield text
                text = ''
        if line['text'][-1] == '-':
            text += line['text'][:-1]
        else:
            text += line['text'] + ' '
    if len(text) > 0:
        yield text


def make_resolution_phrase_model_searcher() -> FuzzyPhraseSearcher:
    resolution_phrase_searcher_config = {
        'filter_distractors': True,
        'include_variants': True,
        'use_word_boundaries': True,
        'max_length_variance': 3,
        'levenshtein_threshold': 0.7,
        'char_match_threshold': 0.7,
        'ngram_size': 3,
        'skip_size': 1
    }
    resolution_phrase_searcher = FuzzyPhraseSearcher(resolution_phrase_searcher_config)

    '''
    phrases = rpm.proposition_reason_phrases + rpm.proposition_closing_phrases + rpm.decision_phrases + \
              rpm.resolution_link_phrases + rpm.prefix_phrases + rpm.organisation_phrases + \
              rpm.location_phrases + rpm.esteem_titles + rpm.person_role_phrases + rpm.military_phrases + \
              rpm.misc + rpm.provinces + rpm.proposition_opening_phrases
    '''

    phrases = []
    for set_name in rpm.resolution_phrase_sets:
        print('adding phrases from set', set_name)
        phrases += rpm.resolution_phrase_sets[set_name]
    # phrases = rpm.proposition_opening_phrases
    # for phrase in phrases:
    #     if 'max_offset' in phrase:
    #         del phrase['max_offset']
    print(f'building phrase model for {len(phrases)} resolution phrases')

    resolution_phrase_phrase_model = PhraseModel(model=phrases, config=resolution_phrase_searcher_config)
    resolution_phrase_searcher.index_phrase_model(resolution_phrase_phrase_model)
    return resolution_phrase_searcher


def get_session_resolutions(session: rdm.Session, opening_searcher: FuzzyPhraseSearcher,
                            verb_searcher: FuzzyPhraseSearcher) -> Generator[rdm.Resolution, None, None]:
    resolution = None
    resolution_number = 0
    attendance_list = None
    generate_id = running_id_generator(session.metadata['id'], '-resolution-')
    session_offset = 0
    print('fuzzy searcher version:', opening_searcher.__version__)
    for paragraph in get_paragraphs(session):
        # print('get_session_resolutions - paragraph:\n', paragraph.text, '\n')
        opening_matches = opening_searcher.find_matches({'text': paragraph.text, 'id': paragraph.metadata['id']})
        verb_matches = verb_searcher.find_matches({'text': paragraph.text, 'id': paragraph.metadata['id']})
        for match in opening_matches + verb_matches:
            match.text_id = paragraph.metadata['id']
            # print('\t', match.offset, '\t', match.string, '\t', match.variant.phrase_string)
        if len(opening_matches) > 0:
            if attendance_list:
                yield attendance_list
                attendance_list = None
            resolution_number += 1
            if resolution:
                yield resolution
            metadata = get_base_metadata(session, generate_id(), 'resolution')
            resolution = rdm.Resolution(doc_id=metadata['id'], metadata=metadata)
            # print('\tCreating new resolution with number:', resolution_number, resolution.metadata['id'])
        if resolution:
            resolution.add_paragraph(paragraph, matches=opening_matches + verb_matches)
        elif attendance_list:
            attendance_list.add_paragraph(paragraph, matches=[])
        else:
            metadata = get_base_metadata(session, session.metadata['id'] + '-attendance_list',
                                         'attendance_list')
            attendance_list = rdm.AttendanceList(doc_id=metadata['id'], metadata=metadata)
            # print('\tCreating new attedance list with number:', 1, attendance_list.metadata['id'])
            attendance_list.add_paragraph(paragraph, matches=[])
        # print('start offset:', session_offset, '\tend offset:', session_offset + len(paragraph.text))
        session_offset += len(paragraph.text)
    if resolution:
        yield resolution


def running_id_generator(base_id: str, suffix: str, count: int = 0):
    """Returns an ID generator based on running numbers."""

    def generate_id():
        nonlocal count
        count += 1
        return f'{base_id}{suffix}{count}'

    return generate_id


def get_base_metadata(source_doc: rdm.RepublicDoc, doc_id: str, doc_type: str) -> Dict[str, Union[str, int]]:
    """Return a dictionary with basic metadata for a structure document."""
    metadata = {
        'inventory_num': source_doc.metadata['inventory_num'],
        'source_id': source_doc.metadata['id'],
        'type': doc_type,
        'id': doc_id
    }
    if doc_type in ["resolution", "attendance_list"]:
        metadata['session_date'] = source_doc.metadata['session_date']
        metadata['session_id'] = source_doc.metadata['id']
        metadata['session_num'] = source_doc.metadata['session_num']
        metadata['inventory_num'] = source_doc.metadata['inventory_num']
        metadata['president'] = source_doc.metadata['president']
        metadata['session_year'] = source_doc.metadata['session_year']
        metadata['session_month'] = source_doc.metadata['session_month']
        metadata['session_day'] = source_doc.metadata['session_day']
        metadata['session_weekday'] = source_doc.metadata['session_weekday']
    return metadata


def get_paragraphs(session: rdm.Session, prev_line: Union[None, dict] = None,
                   word_freq_counter: Counter = None) -> Generator[rdm.RepublicParagraph, None, None]:
    if session.paragraphs:
        for paragraph in session.paragraphs:
            yield paragraph
    else:
        text_page_num_map = {}
        for tr in session.text_regions:
            text_page_num_map[tr.id] = tr.metadata["text_page_num"]
        if 1705 <= session.date.date.year < 1711:
            paragraphs = get_paragraphs_with_indent(session, prev_line=prev_line,
                                                    word_freq_counter=word_freq_counter,
                                                    text_page_num_map=text_page_num_map)
        elif session.date.date.year >= 1711:
            paragraphs = get_paragraphs_with_vertical_space(session, prev_line=prev_line,
                                                            word_freq_counter=word_freq_counter,
                                                            text_page_num_map=text_page_num_map)
        else:
            paragraphs = []
        for paragraph in paragraphs:
            paragraph.metadata['doc_id'] = session.metadata['id']
            yield paragraph


def make_paragraph(doc: rdm.RepublicDoc, doc_text_offset: int, paragraph_id: str,
                   para_lines: List[pdm.PageXMLTextLine],
                   word_freq_counter: Counter) -> rdm.RepublicParagraph:
    metadata = get_base_metadata(doc, paragraph_id, "resolution_paragraph")
    paragraph = rdm.RepublicParagraph(lines=para_lines, metadata=metadata,
                                      word_freq_counter=word_freq_counter)
    paragraph.metadata["start_offset"] = doc_text_offset
    return paragraph


def is_paragraph_boundary(prev_line, line, next_line) -> bool:
    if prev_line and pdm.same_column(line, prev_line):
        if line.is_next_to(prev_line):
            # print("SAME HEIGHT", prev_line['text'], '\t', line['text'])
            return False
        elif line.coords.left > prev_line.coords.left + 20:
            # this line is left indented w.r.t. the previous line
            # so is the start of a new paragraph
            return True
        elif line.coords.left - prev_line.coords.left < 20:
            if line.coords.right > prev_line.coords.right + 40:
                # this line starts at the same horizontal level as the previous line
                # but the previous line ends early, so is the end of a paragraph.
                return True
            else:
                return False
    elif next_line and pdm.same_column(line, next_line):
        if line.coords.left > next_line.coords.left + 20:
            return True
    return False


def get_paragraphs_with_indent(doc: rdm.RepublicDoc, prev_line: Union[None, pdm.PageXMLTextLine] = None,
                               word_freq_counter: Counter = None,
                               text_page_num_map: Dict[str, int] = None) -> List[rdm.RepublicParagraph]:
    paragraphs: List[rdm.RepublicParagraph] = []
    generate_paragraph_id = running_id_generator(base_id=doc.metadata['id'], suffix='-para-')
    para_lines = []
    doc_text_offset = 0
    lines = [line for line in doc.get_lines()]
    for li, line in enumerate(lines):
        if text_page_num_map is not None and line.metadata["parent_id"] in text_page_num_map:
            line.metadata["text_page_num"] = text_page_num_map[line.metadata["parent_id"]]
        next_line = lines[li + 1] if len(lines) > (li + 1) else None
        if is_paragraph_boundary(prev_line, line, next_line):
            if len(para_lines) > 0:
                paragraph = make_paragraph(doc, doc_text_offset, generate_paragraph_id(),
                                           para_lines, word_freq_counter)
                doc_text_offset += len(paragraph.text)
                paragraphs.append(paragraph)
            para_lines = []
        para_lines.append(line)
        if not line.text or len(line.text) == 1:
            continue
        if prev_line and line.is_next_to(prev_line):
            continue
        # if prev_line and line.text and line.is_next_to(prev_line):
        # words = re.split(r"\W+", line.text)
        # word_counts = [word_freq_counter[word] for word in words if word != ""]
        prev_line = line
    if len(para_lines) > 0:
        paragraph = make_paragraph(doc, doc_text_offset, generate_paragraph_id(),
                                   para_lines, word_freq_counter)
        doc_text_offset += len(paragraph.text)
        paragraphs.append(paragraph)
    return paragraphs


def get_paragraphs_with_vertical_space(doc: rdm.RepublicDoc, prev_line: Union[None, dict] = None,
                                       word_freq_counter: Counter = None,
                                       text_page_num_map: Dict[str, int] = None) -> List[rdm.RepublicParagraph]:
    para_lines = []
    paragraphs = []
    doc_text_offset = 0
    generate_paragraph_id = running_id_generator(base_id=doc.metadata["id"], suffix="-para-")
    lines = [line for line in doc.get_lines()]
    # print('getting paragraphs with vertical space')
    for li, line in enumerate(lines):
        if text_page_num_map is not None and line.metadata["parent_id"] in text_page_num_map:
            line.metadata["text_page_num"] = text_page_num_map[line.metadata["parent_id"]]
        # if prev_line:
        #     print(prev_line.coords.top, prev_line.coords.bottom, line.coords.top, line.coords.bottom, line.text)
        if is_resolution_gap(prev_line, line):
            if len(para_lines) > 0:
                paragraph = make_paragraph(doc, doc_text_offset, generate_paragraph_id(),
                                           para_lines, word_freq_counter)
                doc_text_offset += len(paragraph.text)
                # print('appending paragraph:', paragraph.id)
                # print(paragraph.text)
                # print()
                paragraphs.append(paragraph)
            para_lines = []
        para_lines.append(line)
        if not line.text or len(line.text) == 1:
            continue
        if prev_line and line.is_next_to(prev_line):
            continue
        prev_line = line
    if len(para_lines) > 0:
        metadata = get_base_metadata(doc, generate_paragraph_id(), "resolution_paragraph")
        paragraph = rdm.RepublicParagraph(lines=para_lines, metadata=metadata,
                                          word_freq_counter=word_freq_counter)
        paragraph.metadata['start_offset'] = doc_text_offset
        doc_text_offset += len(paragraph.text)
        paragraphs.append(paragraph)
    return paragraphs


def is_resolution_gap(prev_line: pdm.PageXMLTextLine, line: pdm.PageXMLTextLine) -> bool:
    if not prev_line:
        return False
    # Resolution start line has big capital with low bottom.
    # If gap between box bottoms is small, this is no resolution gap.
    if -20 < line.coords.bottom - prev_line.coords.bottom < 80:
        # print('is_resolution_gap: False', line.coords.bottom - prev_line.coords.bottom)
        return False
    # If this line starts with a big capital, this is a resolution gap.
    if pagexml.line_starts_with_big_capital(line):
        # print('is_resolution_gap: True, line starts with capital')
        return True
    # If the previous line has no big capital starting a resolution,
    # and it has a large vertical gap with the current line,
    # this is resolution gap.
    if not pagexml.line_starts_with_big_capital(prev_line) and line.coords.top - prev_line.coords.top > 70:
        # print('is_resolution_gap: True', line.coords.bottom - prev_line.coords.bottom)
        return True
    else:
        # print('is_resolution_gap: False', line.coords.bottom - prev_line.coords.bottom)
        return False


def configure_resolution_searchers():
    opening_searcher_config = {
        "char_match_threshold": 0.7,
        "ngram_threshold": 0.6,
        "levenshtein_threshold": 0.7,
        'filter_distractors': True,
        'include_variants': True,
        'ngram_size': 3,
        'skip_size': 1,
        'max_length_variance': 3
    }
    opening_searcher = FuzzyPhraseSearcher(opening_searcher_config)
    opening_phrase_model = PhraseModel(model=rpm.proposition_opening_phrases, config=opening_searcher_config)
    opening_searcher.index_phrase_model(opening_phrase_model)
    verb_searcher_config = {
        "char_match_threshold": 0.7,
        "ngram_threshold": 0.6,
        "levenshtein_threshold": 0.7,
        'ngram_size': 3,
        'skip_size': 1,
        'max_length_variance': 1
    }
    verb_searcher = FuzzyPhraseSearcher(verb_searcher_config)
    verb_phrase_model = PhraseModel(model=rpm.proposition_verbs, config=verb_searcher_config)
    verb_searcher.index_phrase_model(verb_phrase_model)
    return opening_searcher, verb_searcher
