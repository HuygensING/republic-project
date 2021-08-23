from typing import Dict, List, Set, Union, Tuple
from collections import defaultdict
import copy
from elasticsearch import Elasticsearch
from fuzzy_search.fuzzy_phrase_model import PhraseModel
from fuzzy_search.fuzzy_phrase_searcher import FuzzyPhraseSearcher

from republic.model.republic_document_model import parse_phrase_match, PhraseMatch, RepublicParagraph, Resolution
from fuzzy_search.fuzzy_template_searcher import FuzzyTemplateSearcher, FuzzyTemplate, TemplateMatch
from republic.model.resolution_templates import opening_templates
from republic.model.resolution_phrase_model import resolution_phrase_sets as rps
import republic.elastic.republic_elasticsearch as rep_es


class VariableMatcher:

    def __init__(self, length_min: int, length_max: int, template: FuzzyTemplate):
        self.length_min = length_min
        self.length_max = length_max
        self.has_variable = defaultdict(set)
        self.template = template
        for element in template.root_element.elements:
            for subelement in element.elements:
                if subelement.variable:
                    self.has_variable[element.label].add(subelement.label)

    def infix_variable_group(self, prev_group_label: str, curr_group_label: str) -> Union[None, List[str]]:
        group_labels = [element.label for element in self.template.root_element.elements]
        infix_start = group_labels.index(prev_group_label) + 1
        infix_end = group_labels.index(curr_group_label)
        return group_labels[infix_start:infix_end] if infix_end > infix_start else None

    def within_variable_length_threshold(self, prev_match: PhraseMatch, curr_match: PhraseMatch) -> int:
        start = 0 if not prev_match else prev_match.end
        end = curr_match.offset
        return self.length_min <= end - start <= self.length_max

    def add_variable_phrases(self, template_match: TemplateMatch,
                             paragraph: RepublicParagraph) -> List[Dict[str, any]]:
        prev_phrase_match = None
        prev_element_match = None
        prev_group_label = None
        extended_elements = []
        for element_match in template_match.element_matches:
            curr_group_label = element_match['label_groups'][0]
            if len(element_match["phrase_matches"]) == 0:
                continue
            for phrase_match in element_match["phrase_matches"]:
                phrase_start = phrase_match.offset
                if self.within_variable_length_threshold(prev_phrase_match, phrase_match):
                    prev_end = 0 if not prev_phrase_match else prev_phrase_match.end
                    variable_entity_string = paragraph.text[prev_end:phrase_start].strip()
                    variable_match = make_variable_phrase_match(variable_entity_string, prev_end,
                                                                phrase_start, paragraph.metadata['id'])
                    if prev_group_label != curr_group_label and prev_group_label in self.has_variable:
                        variable_element = copy.deepcopy(prev_element_match)
                    elif curr_group_label in self.has_variable:
                        variable_element = copy.deepcopy(element_match)
                    elif self.infix_variable_group(prev_group_label, curr_group_label):
                        variable_element = copy.deepcopy(element_match)
                        label = self.infix_variable_group(prev_group_label, curr_group_label)[0]
                        variable_element['label_groups'] = [label]
                    else:
                        print('SKIPPING VARIABLE PASSAGE:')
                        print('\tprevious group label:', prev_group_label)
                        print('\tcurrent group label:', curr_group_label)
                        print('\t', variable_entity_string, '\n')
                        variable_element = None
                    if variable_element:
                        variable_element['label_groups'] = [variable_element['label_groups'][0], 'variable_entity']
                        variable_element['phrase_matches'] = [variable_match]
                        variable_element['label'] = 'variable_entity'
                        extended_elements.append(variable_element)
                # phrase_end = phrase_start + len(phrase_match.string)
                # if not prev_phrase_match or phrase_match.offset > prev_phrase_match.offset:
                #    print(f"\t{element_match['label_groups'][0]: <20}{element_match['label']: <25}" \
                #          + f"{phrase_match.string: <30}{phrase_match.variant.phrase_string}")
                prev_phrase_match = phrase_match
                prev_group_label = curr_group_label
                if curr_group_label == 'proposition_verb':
                    break
            prev_element_match = element_match
            extended_elements.append(element_match)
        return extended_elements


def get_paragraph_phrase_matches(es: Elasticsearch, resolution: Resolution,
                                 config: Dict[str, any]) -> List[PhraseMatch]:
    opening_para = resolution.paragraphs[0]
    para_id = opening_para.metadata['id']
    phrase_matches = rep_es.retrieve_phrase_matches_by_paragraph_id(es, para_id, config)
    # extra_matches = add_evidence_matches(phrase_matches, resolution.evidence)
    return filter_matches(phrase_matches)


def add_evidence_matches(phrase_matches: List[PhraseMatch], resolution: Resolution):
    extra_matches = []
    for match in resolution.evidence:
        skip = False
        for phrase_match in phrase_matches:
            if match.offset == phrase_match.offset and match.phrase.phrase_string == phrase_match.phrase.phrase_string:
                skip = True
        if not skip:
            extra_matches.append(match)
    return extra_matches


def filter_matches(phrase_matches: List[PhraseMatch]) -> List[PhraseMatch]:
    filtered_matches = []
    phrase_matches.sort(key=lambda match: match.offset)
    for phrase_match in phrase_matches:
        if phrase_match != phrase_matches[0] and phrase_match.offset < phrase_matches[0].end \
                and phrase_matches[0].has_label('proposition_opening'):
            continue
        if phrase_match.has_label('proposition_verb') or phrase_match.has_label('person_name_prefix'):
            if phrase_match.levenshtein_similarity and phrase_match.levenshtein_similarity <= 0.8:
                continue
        if phrase_match != phrase_matches[0] and phrase_match.end < phrase_matches[0].end:
            continue
        filtered_matches.append(phrase_match)
    return [match for match in filtered_matches if
            not match.levenshtein_similarity or match.levenshtein_similarity >= 0.65]


def make_variable_phrase_match(string: str, offset: int, end: int, text_id: str) -> PhraseMatch:
    match_json = {
        'phrase': string,
        'variant': string,
        'string': string,
        'offset': offset,
        'end': end,
        'text_id': text_id,
        'label': 'variable_entity'
    }
    return parse_phrase_match(match_json)


def generate_resolution_metadata(phrase_matches: List[PhraseMatch], resolution: Resolution,
                                 opening_searcher: FuzzyTemplateSearcher,
                                 variable_matcher: VariableMatcher) -> Union[None, Dict[str, List[dict]]]:
    metadata = defaultdict(list)
    template_matches = opening_searcher.find_template_matches(phrase_matches)
    if len(template_matches) == 0:
        return None
    template_match = template_matches[0]
    prev_phrase_match = None
    extended_elements = variable_matcher.add_variable_phrases(template_match, resolution.paragraphs[0])
    for element_match in extended_elements:
        group_label = element_match['label_groups'][0]
        if len(element_match["phrase_matches"]) == 0:
            continue
        for phrase_match in element_match["phrase_matches"]:
            if not prev_phrase_match or phrase_match.offset > prev_phrase_match.offset:
                metadata[group_label].append({
                    'group_label': group_label,
                    'element_label': element_match['label'],
                    'phrase': phrase_match.phrase.phrase_string,
                    'evidence': phrase_match.json()
                })
            prev_phrase_match = phrase_match
            if group_label == 'proposition_verb':
                break
        if group_label == 'proposition_verb':
            break
    for group in metadata:
        group_start = metadata[group][0]['evidence']['offset']
        group_end = metadata[group][-1]['evidence']['offset'] + len(metadata[group][-1]['evidence']['string'])
        full_string = resolution.paragraphs[0].text[group_start:group_end]
        metadata[group].append({
            'element_label': 'full_string',
            'phrase': full_string
        })
    return metadata


def skip_resolution(resolution: Resolution, phrase_matches: List[PhraseMatch],
                    skip_formulas: Set[str]) -> bool:
    opening_para = resolution.paragraphs[0]
    if not resolution.metadata['proposition_type']:
        print(f'Resolution paragraph {opening_para.metadata["id"]}:\n\t', opening_para.text, '\n')
        for match in phrase_matches:
            print(match.phrase.phrase_string, '\t', match.string, '\t', match.label, '\t', match.levenshtein_similarity)
    skip = False
    for pm in phrase_matches:
        if pm.phrase.phrase_string in skip_formulas:
            skip = True
            break
    return skip


def add_resolutions_metadata(es: Elasticsearch, resolutions: List[Resolution], config: dict,
                             opening_searcher: FuzzyTemplateSearcher):
    variable_matcher = VariableMatcher(6, 100, opening_searcher.template)
    skip_formulas = {
        'heeft aan haar Hoog Mog. voorgedragen',
        'heeft ter Vergadering gecommuniceert ',
        'ZYnde ter Vergaderinge geëxhibeert vier Pasporten van',
        'hebben ter Vergaderinge ingebraght',
        'hebben ter Vergaderinge voorgedragen'
    }
    metadata_docs = []
    for resolution in resolutions:
        phrase_matches = get_paragraph_phrase_matches(es, resolution, config)
        if skip_resolution(resolution, phrase_matches, skip_formulas):
            continue
        resolution = add_resolution_metadata(resolution, phrase_matches, opening_searcher, variable_matcher)
        if not resolution:
            continue
        metadata_doc = {
            'metadata': resolution.metadata,
            'evidence': [pm.json() for pm in resolution.evidence]
        }
        metadata_docs.append(metadata_doc)
    return metadata_docs


def add_resolution_metadata(resolution: Resolution, proposition_searcher: FuzzyPhraseSearcher,
                            opening_searcher: FuzzyTemplateSearcher,
                            variable_matcher: VariableMatcher) -> Union[None, Resolution]:
    resolution = copy.deepcopy(resolution)
    opening_paragraph = resolution.paragraphs[0]
    proposition_text = get_resolution_proposition_text(resolution)
    doc = {'id': opening_paragraph.metadata['id'], 'text': proposition_text}
    phrase_matches = proposition_searcher.find_matches(doc)
    phrase_matches = filter_matches(phrase_matches)
    import json
    try:
        metadata = generate_resolution_metadata(phrase_matches, resolution, opening_searcher, variable_matcher)
    except ValueError:
        print(f'Resolution paragraph {opening_paragraph.metadata["id"]}:\n\t', opening_paragraph.text, '\n')
        for match in phrase_matches:
            print(match.phrase.phrase_string, '\t', match.string, '\t', match.label, '\t', match.levenshtein_similarity)
        return resolution
    # print(json.dumps(metadata, indent=4))
    if metadata:
        # evidence = [element['evidence'] for group in metadata for element in metadata[group] if 'evidence' in element]
        resolution.evidence = phrase_matches
        for metadata_group in metadata:
            group_info = {}
            for element in metadata[metadata_group]:
                label = element['element_label']
                if label in group_info:
                    if isinstance(group_info[label], str):
                        group_info[label] = [group_info[label]]
                    group_info[label].append(element['phrase'])
                else:
                    group_info[label] = element['phrase']
            # group_info = {element['element_label']: element['phrase'] for element in metadata[metadata_group]}
            resolution.metadata[metadata_group] = group_info

    # print('resolution metadata:')
    # print(json.dumps(resolution.metadata, indent=2))
    return resolution


def get_resolution_proposition_text(resolution: Resolution) -> str:
    proposition_end = len(resolution.paragraphs[0].text)
    for pm in resolution.evidence:
        # print(pm.offset, pm.label, pm.levenshtein_similarity)
        if pm.has_label('proposition_verb') and pm.levenshtein_similarity > 0.7:
            proposition_end = pm.end
            break
    proposition_text = resolution.paragraphs[0].text[:proposition_end]
    return proposition_text


def generate_proposition_searchers(searcher_config: Dict[str, any] = None):
    if not searcher_config:
        searcher_config = {
            'filter_distractors': True,
            'include_variants': True,
            'max_length_variance': 3,
            'levenshtein_threshold': 0.7,
            'char_match_threshold': 0.7,
            'use_word_boundaries': True,
            'ngram_size': 3,
            'skip_size': 1
        }
    phrases = [phrase for phrase_set in rps for phrase in rps[phrase_set]]
    return generate_template_searchers(opening_templates[0], phrases, searcher_config)


def generate_template_searchers(template: Dict[str, any], phrases: List[Dict[str, any]],
                                searcher_config: dict) -> Tuple[FuzzyPhraseSearcher, FuzzyTemplateSearcher, VariableMatcher]:
    proposition_searcher = FuzzyPhraseSearcher(searcher_config)
    proposition_phrase_model = PhraseModel(model=phrases, config=searcher_config)
    proposition_searcher.index_phrase_model(proposition_phrase_model)
    opening_template = FuzzyTemplate(proposition_phrase_model, template)
    template_searcher = FuzzyTemplateSearcher(opening_template, searcher_config)
    variable_matcher = VariableMatcher(6, 100, template_searcher.template)
    return proposition_searcher, template_searcher, variable_matcher
