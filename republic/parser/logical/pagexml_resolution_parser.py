import copy
from typing import Dict, Generator, List, Tuple, Union

from fuzzy_search.search.phrase_searcher import FuzzyPhraseSearcher
from fuzzy_search.phrase.phrase_model import PhraseModel
from langdetect import detect_langs, LangDetectException

import republic.helper.paragraph_helper as para_helper
import republic.model.physical_document_model as pdm
import republic.model.republic_document_model as rdm
import republic.model.resolution_phrase_model as rpm
from republic.parser.logical.paragraph_parser import ParagraphGenerator
from republic.parser.logical.paragraph_parser import running_id_generator
from republic.helper.metadata_helper import doc_id_to_iiif_url
from republic.helper.paragraph_helper import LineBreakDetector


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
        # print('adding phrases from set', set_name)
        phrases += rpm.resolution_phrase_sets[set_name]
    # phrases = rpm.proposition_opening_phrases
    # for phrase in phrases:
    #     if 'max_offset' in phrase:
    #         del phrase['max_offset']
    print(f'building phrase model for {len(phrases)} resolution phrases')

    resolution_phrase_model = PhraseModel(model=phrases, config=resolution_phrase_searcher_config)
    resolution_phrase_searcher.index_phrase_model(resolution_phrase_model)
    for phrase in resolution_phrase_searcher.phrases:
        if phrase.has_label('proposition_opening'):
            custom = resolution_phrase_model.custom[phrase.phrase_string]
            if 'proposition_type' in custom:
                label_set = phrase.label_set
                label_set.add(f"proposition_type:{custom['proposition_type']}")
                phrase.label = list(label_set)
    return resolution_phrase_searcher


def get_resolution_text_page_nums(res_doc: Union[rdm.Resolution, rdm.AttendanceList]) -> List[int]:
    text_page_nums = set()
    for para in res_doc.paragraphs:
        for text_page_num in para.metadata["text_page_num"]:
            if isinstance(text_page_num, int):
                text_page_nums.add(text_page_num)
    return sorted(list(text_page_nums))


def get_resolution_page_nums(res_doc: Union[rdm.Resolution, rdm.AttendanceList]) -> List[int]:
    page_nums = set()
    for para in res_doc.paragraphs:
        for page_num in para.metadata["page_num"]:
            if isinstance(page_num, int):
                page_nums.add(page_num)
    return sorted(list(page_nums))


def get_resolution_page_ids(res_doc: Union[rdm.Resolution, rdm.AttendanceList]) -> List[int]:
    page_ids = set()
    for para in res_doc.paragraphs:
        if 'page_ids' not in para.metadata:
            continue
        for page_id in para.metadata["page_ids"]:
            page_ids.add(page_id)
    return sorted(list(page_ids))


def map_alt_langs(langs):
    alt_langs = {
        # Dutch is often confused with
        'af': 'nl',  # Afrikaans
        'da': 'nl',  # Danish
        'no': 'nl',  # Norwegian
        'sl': 'nl',  # Slovenian
        'sv': 'nl',  # Swedish
        # Latin is often confused with
        'ca': 'la',  # Catalan
        'es': 'la',  # Spanish
        'it': 'la',  # Italian
        'pt': 'la',  # Portuguese
        'ro': 'la',  # Romanian
    }
    lang_dict = {lang.lang: lang for lang in langs}
    lang_list = list(lang_dict.keys())
    for lang in lang_list:
        if lang in alt_langs:
            main_lang = alt_langs[lang]
            if main_lang not in lang_dict:
                lang_dict[main_lang] = copy.deepcopy(lang_dict[lang])
                lang_dict[main_lang].lang = main_lang
            else:
                lang_dict[main_lang].prob += lang_dict[lang].prob
            lang_dict[lang].prob = 0.0
            del lang_dict[lang]
    return list(lang_dict.values())


def determine_language(text):
    try:
        langs = detect_langs(text)
        langs = map_alt_langs(langs)
    except LangDetectException:
        langs = []
    langs.sort(key=lambda x: x.prob, reverse=True)
    if len(langs) == 0:
        text_lang = 'unknown'
    elif len(langs) == 1:
        if len(text) > 100:
            text_lang = langs[0].lang
        elif langs[0].lang in {'fr', 'nl'}:
            text_lang = langs[0].lang
        elif len(text) < 40:
            text_lang = 'unknown'
        else:
            text_lang = 'unknown'
    elif len(text) < 40:
        text_lang = 'unknown'
    elif langs[0].prob > 0.6 and langs[0].lang in {'fr', 'la', 'nl'}:
        text_lang = langs[0].lang
    else:
        text_lang = 'unknown'
    return text_lang


def get_session_resolutions(session: rdm.Session, opening_searcher: FuzzyPhraseSearcher,
                            verb_searcher: FuzzyPhraseSearcher,
                            line_break_detector: LineBreakDetector = None,
                            word_break_chars: str = None) -> Generator[rdm.Resolution, None, None]:
    resolution = None
    resolution_number = 0
    attendance_list = None
    generate_id = running_id_generator(session.id, '-resolution-')
    session_offset = 0
    para_generator = SessionParagraphGenerator(line_break_detector=line_break_detector,
                                               word_break_chars=word_break_chars)
    for paragraph in para_generator.get_paragraphs(session):
        paragraph.metadata['lang'] = determine_language(paragraph.text)
        # print('get_session_resolutions - paragraph:\n', paragraph.text[:500], '\n')
        opening_matches = opening_searcher.find_matches({'text': paragraph.text, 'id': paragraph.id})
        verb_matches = verb_searcher.find_matches({'text': paragraph.text, 'id': paragraph.id})
        for match in opening_matches + verb_matches:
            match.text_id = paragraph.id
            # print('\t', match.offset, '\t', match.string, '\t', match.variant.phrase_string)
        if len(opening_matches) > 0 and opening_matches[0].has_label('reviewed'):
            paragraph.add_type('reviewed')
        elif len(opening_matches) > 0:
            if attendance_list:
                attendance_list.metadata["text_page_num"] = get_resolution_text_page_nums(attendance_list)
                attendance_list.metadata["page_num"] = get_resolution_page_nums(attendance_list)
                attendance_list.metadata["page_ids"] = get_resolution_page_ids(attendance_list)
                yield attendance_list
                attendance_list = None
            resolution_number += 1
            if resolution:
                resolution.set_proposition_type()
                resolution.metadata["text_page_num"] = get_resolution_text_page_nums(resolution)
                resolution.metadata["page_num"] = get_resolution_page_nums(resolution)
                resolution.metadata["page_ids"] = get_resolution_page_ids(resolution)
                yield resolution
            metadata = get_base_metadata(session, generate_id(), 'resolution')
            resolution = rdm.Resolution(doc_id=metadata['id'], metadata=metadata,
                                        evidence=opening_matches + verb_matches)
            # print('\tCreating new resolution with number:', resolution_number, resolution.id)
        if resolution:
            resolution.add_paragraph(paragraph, matches=opening_matches + verb_matches)
            resolution.evidence += opening_matches + verb_matches
        elif attendance_list:
            attendance_list.add_paragraph(paragraph, matches=[])
        else:
            metadata = get_base_metadata(session, session.id + '-attendance_list',
                                         'attendance_list')
            attendance_list = rdm.AttendanceList(doc_id=metadata['id'], metadata=metadata)
            # print('\tCreating new attedance list with number:', 1, attendance_list.id)
            attendance_list.add_paragraph(paragraph, matches=[])
        # print('start offset:', session_offset, '\tend offset:', session_offset + len(paragraph.text))
        session_offset += len(paragraph.text)
    if resolution:
        resolution.metadata['lang'] = list({para.metadata['lang'] for para in resolution.paragraphs})
        resolution.set_proposition_type()
        resolution.metadata["text_page_num"] = get_resolution_text_page_nums(resolution)
        resolution.metadata["page_num"] = get_resolution_page_nums(resolution)
        resolution.metadata["page_ids"] = get_resolution_page_ids(resolution)
        yield resolution


def get_base_metadata(source_doc: rdm.RepublicDoc, doc_id: str, doc_type: str) -> Dict[str, Union[str, int, list]]:
    """Return a dictionary with basic metadata for a structure document."""
    metadata = {
        'inventory_num': source_doc.metadata['inventory_num'],
        'source_id': source_doc.id,
        'type': doc_type,
        'id': doc_id,
        'page_ids': []
    }
    if doc_type in ["resolution", "attendance_list"]:
        metadata['session_date'] = source_doc.metadata['session_date']
        metadata['session_id'] = source_doc.id
        metadata['session_num'] = source_doc.metadata['session_num']
        metadata['inventory_num'] = source_doc.metadata['inventory_num']
        metadata['president'] = source_doc.metadata['president']
        metadata['session_year'] = source_doc.metadata['session_year']
        metadata['session_month'] = source_doc.metadata['session_month']
        metadata['session_day'] = source_doc.metadata['session_day']
        metadata['session_weekday'] = source_doc.metadata['session_weekday']
    return metadata


def make_line_text(line: pdm.PageXMLTextLine, do_merge: bool,
                   end_word: str, merge_word: str) -> str:
    line_text = line.text
    if len(line_text) >= 2 and line_text.endswith('--'):
        # remove the redundant hyphen
        line_text = line_text[:-1]
    if do_merge:
        if line_text[-1] == '-' and merge_word.startswith(end_word) is False:
            # the merge word does not contain a hyphen, so remove it from the line
            # before adding it to the text
            line_text = line_text[:-1]
        else:
            # the line contains no hyphen or the merge word contains the hyphen as
            # well, so leave it in.
            line_text = line.text
    else:
        # no need to meed so add line with trailing whitespace
        if line_text[-1] == '-' and len(line_text) >= 2 and line_text[-2] != ' ':
            # the hyphen at the end is trailing, so disconnect it from the preceding word
            line_text = line_text[:-1] + ' - '
        else:
            line_text = line_text + ' '
    return line_text


def make_line_range(text: str, line: pdm.PageXMLTextLine, line_text: str) -> Dict[str, any]:
    return {
        "start": len(text), "end": len(text + line_text),
        "line_id": line.id,
        "text_page_num": line.metadata["text_page_num"] if "text_page_num" in line.metadata else None,
        "page_num": line.metadata["page_num"] if "page_num" in line.metadata else None
    }


class SessionParagraphGenerator(ParagraphGenerator):

    def __init__(self, line_break_detector: LineBreakDetector = None, word_break_chars: str = None):
        super().__init__(line_break_detector=line_break_detector, word_break_chars=word_break_chars)

    def get_paragraphs(self, session: rdm.Session,
                       prev_line: Union[None, dict] = None) -> Generator[rdm.RepublicParagraph, None, None]:
        if hasattr(session, 'paragraphs') and session.paragraphs:
            for paragraph in session.paragraphs:
                yield paragraph
        else:
            text_page_num_map = {}
            page_num_map = {}
            for tr in session.text_regions:
                if "text_page_num" not in tr.metadata:
                    # print("MISSING text_page_num in session", session.id)
                    pass
                elif tr.metadata["text_page_num"] is not None:
                    text_page_num_map[tr.id] = tr.metadata["text_page_num"]
                page_num_map[tr.id] = tr.metadata["page_num"]
            if 1705 <= session.date.date.year < 1711:
                paragraphs = self.get_paragraphs_with_indent(session, prev_line=prev_line,
                                                             text_page_num_map=text_page_num_map,
                                                             page_num_map=page_num_map)
            elif session.date.date.year < 1705 or session.date.date.year >= 1711:
                paragraphs = self.get_paragraphs_with_vertical_space(session, prev_line=prev_line,
                                                                     text_page_num_map=text_page_num_map,
                                                                     page_num_map=page_num_map)
            else:
                paragraphs = []
            for paragraph in paragraphs:
                paragraph.metadata['doc_id'] = session.id
                yield paragraph

    def make_paragraph(self, doc: rdm.RepublicDoc, doc_text_offset: int, paragraph_id: str,
                       para_lines: List[pdm.PageXMLTextLine]) -> rdm.RepublicParagraph:
        metadata = get_base_metadata(doc, paragraph_id, "resolution_paragraph")
        text_region_ids = []
        for line in para_lines:
            if line.metadata["parent_id"] not in text_region_ids:
                text_region_ids.append(line.metadata["parent_id"])
                if line.metadata['page_id'] not in metadata['page_ids']:
                    metadata['page_ids'].append(line.metadata['page_id'])
        text, line_ranges = self.make_paragraph_text(para_lines)
        paragraph = rdm.RepublicParagraph(lines=para_lines, metadata=metadata,
                                          text=text, line_ranges=line_ranges)
        paragraph.metadata["start_offset"] = doc_text_offset
        paragraph.metadata["iiif_url"] = []
        for text_region_id in text_region_ids:
            paragraph.metadata["iiif_url"].append(doc_id_to_iiif_url(text_region_id))
        if len(paragraph.metadata["iiif_url"]) == 1:
            paragraph.metadata["iiif_url"] = paragraph.metadata["iiif_url"][0]
        return paragraph

    """
    def make_paragraph_text(self, lines: List[pdm.PageXMLTextLine]) -> Tuple[str, List[Dict[str, any]]]:
        text = ''
        line_ranges = []
        prev_line = lines[0]
        prev_words = para_helper.get_line_words(prev_line.text) if prev_line.text else []
        if len(lines) > 1:
            for curr_line in lines[1:]:
                if curr_line.text is None:
                    continue
                curr_words = para_helper.get_line_words(curr_line.text)
                do_merge, merge_word = para_helper.determine_line_break(self.lbd,
                                                                        curr_words, prev_words)
                prev_line_text = make_line_text(prev_line, do_merge, prev_words[-1], merge_word)
                if prev_line.text is not None:
                    line_range = make_line_range(text, prev_line, prev_line_text)
                    line_ranges.append(line_range)
                    text += prev_line_text
                prev_words = curr_words
                prev_line = curr_line
        # add the last line (without adding trailing whitespace)
        if prev_line.text is not None:
            line_range = make_line_range(text, prev_line, prev_line.text)
            line_ranges.append(line_range)
            text += prev_line.text
        return text, line_ranges

    def get_paragraphs_with_indent(self, doc: rdm.RepublicDoc, prev_line: Union[None, pdm.PageXMLTextLine] = None,
                                   text_page_num_map: Dict[str, int] = None,
                                   page_num_map: Dict[str, int] = None) -> List[rdm.RepublicParagraph]:
        paragraphs: List[rdm.RepublicParagraph] = []
        generate_paragraph_id = running_id_generator(base_id=doc.id, suffix='-para-')
        para_lines = []
        doc_text_offset = 0
        lines = [line for line in doc.get_lines()]
        for li, line in enumerate(lines):
            if text_page_num_map is not None and line.metadata["parent_id"] in text_page_num_map:
                line.metadata["text_page_num"] = text_page_num_map[line.metadata["parent_id"]]
            line.metadata["page_num"] = page_num_map[line.metadata["parent_id"]]
            next_line = lines[li + 1] if len(lines) > (li + 1) else None
            if is_paragraph_boundary(prev_line, line, next_line):
                if len(para_lines) > 0:
                    paragraph = self.make_paragraph(doc, doc_text_offset, generate_paragraph_id(),
                                                    para_lines)
                    doc_text_offset += len(paragraph.text)
                    paragraphs.append(paragraph)
                para_lines = []
            para_lines.append(line)
            if not line.text or len(line.text) == 1:
                continue
            if prev_line and line.is_next_to(prev_line):
                continue
            prev_line = line
        if len(para_lines) > 0:
            paragraph = self.make_paragraph(doc, doc_text_offset, generate_paragraph_id(),
                                            para_lines)
            doc_text_offset += len(paragraph.text)
            paragraphs.append(paragraph)
        return paragraphs

    def get_paragraphs_with_vertical_space(self, doc: rdm.RepublicDoc, prev_line: Union[None, dict] = None,
                                           text_page_num_map: Dict[str, int] = None,
                                           page_num_map: Dict[str, int] = None) -> List[rdm.RepublicParagraph]:
        para_lines = []
        paragraphs = []
        doc_text_offset = 0
        generate_paragraph_id = running_id_generator(base_id=doc.metadata["id"], suffix="-para-")
        if isinstance(doc, rdm.Session) and doc.date.date.year < 1705:
            resolution_gap = 120
            margin_trs = []
            body_trs = []
            for tr in doc.text_regions:
                left_margin = 800 if tr.metadata['page_num'] % 2 == 0 else 3100
                if tr.coords.x < left_margin and tr.coords.width < 1000:
                    margin_trs.append(tr)
                else:
                    body_trs.append(tr)
            lines = [line for tr in body_trs for line in tr.lines]
        else:
            resolution_gap = 80
            lines = [line for line in doc.get_lines()]
        # print('getting paragraphs with vertical space')
        for li, line in enumerate(lines):
            if text_page_num_map is not None and line.metadata["parent_id"] in text_page_num_map:
                line.metadata["text_page_num"] = text_page_num_map[line.metadata["parent_id"]]
            line.metadata["page_num"] = page_num_map[line.metadata["parent_id"]]
            # if prev_line:
            #     print(prev_line.coords.top, prev_line.coords.bottom, line.coords.top, line.coords.bottom, line.text)
            if is_resolution_gap(prev_line, line, resolution_gap):
                if len(para_lines) > 0:
                    paragraph = self.make_paragraph(doc, doc_text_offset,
                                                    generate_paragraph_id(), para_lines)
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
            paragraph = self.make_paragraph(doc, doc_text_offset, generate_paragraph_id(),
                                            para_lines)
            doc_text_offset += len(paragraph.text)
            paragraphs.append(paragraph)
        return paragraphs
    """


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
