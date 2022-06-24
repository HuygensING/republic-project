from typing import Dict, List, Set, Union, Tuple
from collections import defaultdict
import copy

from elasticsearch import Elasticsearch
from fuzzy_search.fuzzy_phrase_model import PhraseModel
from fuzzy_search.fuzzy_phrase_searcher import FuzzyPhraseSearcher
from fuzzy_search.fuzzy_template_searcher import FuzzyTemplateSearcher, FuzzyTemplate, TemplateMatch

from republic.model.republic_document_model import parse_phrase_match, PhraseMatch, RepublicParagraph, Resolution
from republic.model.resolution_templates import opening_templates
from republic.model.resolution_phrase_model import resolution_phrase_sets as rps
from republic.elastic.republic_elasticsearch import RepublicElasticsearch


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
        # print('group_labels:', group_labels)
        infix_start = group_labels.index(prev_group_label) + 1 if prev_group_label else 0
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
        # print(template_match)
        for element_match in template_match.element_matches:
            curr_group_label = element_match['label_groups'][0]
            # print('current group:', curr_group_label)
            if len(element_match["phrase_matches"]) == 0:
                continue
            for phrase_match in element_match["phrase_matches"]:
                phrase_start = phrase_match.offset
                # print('\tphrase match:', phrase_match.offset, phrase_match.string)
                if self.within_variable_length_threshold(prev_phrase_match, phrase_match):
                    prev_end = 0 if not prev_phrase_match else prev_phrase_match.end
                    variable_entity_string = paragraph.text[prev_end:phrase_start].strip()
                    variable_match = make_variable_phrase_match(variable_entity_string, prev_end,
                                                                phrase_start, paragraph.metadata['id'])
                    # print('prev_group_label:', prev_group_label)
                    # print('curr_group_label:', curr_group_label)
                    # print('has_variable:', self.has_variable)
                    if prev_group_label != curr_group_label and prev_group_label in self.has_variable:
                        variable_element = copy.deepcopy(prev_element_match)
                    elif curr_group_label in self.has_variable:
                        variable_element = copy.deepcopy(element_match)
                    elif self.infix_variable_group(prev_group_label, curr_group_label):
                        variable_element = copy.deepcopy(element_match)
                        label = self.infix_variable_group(prev_group_label, curr_group_label)[0]
                        # print('infix variable label:', label)
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


def get_paragraph_phrase_matches(rep_es: RepublicElasticsearch,
                                 resolution: Resolution) -> List[PhraseMatch]:
    opening_para = resolution.paragraphs[0]
    para_id = opening_para.metadata['id']
    phrase_matches = rep_es.retrieve_phrase_matches_by_paragraph_id(para_id)
    # extra_matches = add_evidence_matches(phrase_matches, resolution.evidence)
    return phrase_matches


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


def filter_matches(phrase_matches: List[PhraseMatch], proposition_text: str,
                   similarity_threshold: float = 0.65) -> List[PhraseMatch]:
    filtered_matches = []
    phrase_matches.sort(key=lambda match: match.offset)
    longest_opening = None
    # remove all phrase matches that are beyond the proposition text
    phrase_matches = [pm for pm in phrase_matches if pm.end <= len(proposition_text)]
    # if there are multiple proposition openings, find the longest, most specific one
    for phrase_match in phrase_matches:
        if phrase_match.has_label('proposition_opening'):
            # print('prop opening match:', phrase_match.variant.phrase_string)
            if longest_opening is None:
                longest_opening = phrase_match
                # print('first longest opening match:', longest_opening.variant.phrase_string)
            elif phrase_match.offset == longest_opening.offset and phrase_match.end > longest_opening.end:
                longest_opening = phrase_match
                # print('new longest opening match:', longest_opening.variant.phrase_string)
    # reduce overlapping matches to the best one and
    # remove matches after the proposition verb is reached
    for phrase_match in phrase_matches:
        if phrase_match.has_label('proposition_opening'):
            if phrase_match != longest_opening:
                continue
        if phrase_match.has_label('proposition_verb') or phrase_match.has_label('person_name_prefix'):
            if phrase_match.levenshtein_similarity and phrase_match.levenshtein_similarity <= 0.8:
                continue
        if phrase_match != phrase_matches[0] and phrase_match.end < phrase_matches[0].end:
            continue
        filtered_matches.append(phrase_match)
    # Finally return all matches that meet the similarity threshold
    return [match for match in filtered_matches if
            not match.levenshtein_similarity or match.levenshtein_similarity >= similarity_threshold]


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


def get_template_match_length(template_match: TemplateMatch) -> int:
    first_ele = template_match.element_matches[0]
    start = first_ele['phrase_matches'][0].offset
    last_ele = template_match.element_matches[-1]
    end = last_ele['phrase_matches'][-1].offset + len(last_ele['phrase_matches'][-1].string)
    return end - start


def get_template_matches(template_searchers: List[FuzzyTemplateSearcher], phrase_matches: List[PhraseMatch]):
    return [template_searcher.find_template_matches(phrase_matches)
            for template_searcher in template_searchers]


def get_best_template(template_searchers: Dict[str, FuzzyTemplateSearcher],
                      phrase_matches: List[PhraseMatch]) -> Tuple[str, TemplateMatch]:
    longest_template_length = 0
    longest_template_match = None
    longest_template_name = None
    for template_name in template_searchers:
        template_matches = template_searchers[template_name].find_template_matches(phrase_matches)
        if len(template_matches) == 0:
            continue
        template_match = template_matches[0]
        template_length = get_template_match_length(template_match)
        if template_length > longest_template_length:
            longest_template_length = template_length
            longest_template_match = template_match
            longest_template_name = template_name
    return longest_template_name, longest_template_match


def generate_resolution_metadata(phrase_matches: List[PhraseMatch], resolution: Resolution,
                                 template_searchers: Dict[str, FuzzyTemplateSearcher],
                                 variable_matchers: Dict[str, VariableMatcher]) -> Union[None, Dict[str, List[dict]]]:
    metadata = defaultdict(list)
    # for phrase_match in phrase_matches:
    #     print(phrase_match.offset, phrase_match.phrase.phrase_string, phrase_match.string,
    #           phrase_match.phrase.label_list)
    best_template_name, best_template_match = get_best_template(template_searchers, phrase_matches)
    if best_template_match is None:
        return None
    variable_matcher = variable_matchers[best_template_name]
    extended_elements = variable_matcher.add_variable_phrases(best_template_match, resolution.paragraphs[0])
    if len(extended_elements) == 0:
        return None
    # template_match = template_matches[0]
    # print(template_match.template)
    prev_phrase_match = None
    # extended_elements = variable_matcher.add_variable_phrases(template_match, resolution.paragraphs[0])
    # print()
    for element_match in extended_elements:
        # print(element_match['label'])
        # if element_match['label'] == 'proposition_opening':
        #     for match in element_match['phrase_matches']:
        #         metadata['proposition_type'] = match.phrase.metadata['proposition_type']
        #         print('match label:', match.label)
        #         print('match phrase label:', match.phrase.metadata['proposition_type'])
        #     print(match.offset, match.string)
        group_label = element_match['label_groups'][0]
        if len(element_match["phrase_matches"]) == 0:
            continue
        for phrase_match in element_match["phrase_matches"]:
            if not prev_phrase_match or phrase_match.offset > prev_phrase_match.offset:
                metadata[group_label].append({
                    'group_label': group_label,
                    'element_label': element_match['label'],
                    'phrase': phrase_match.phrase.phrase_string,
                    'evidence': phrase_match.json(),
                    'start_offset': phrase_match.offset,
                    'end_offset': phrase_match.offset + len(phrase_match.string)
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
            'phrase': full_string,
            'start_offset': group_start,
            'end_offset': group_end
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


def get_proposition_origin(resolution_metadata: Dict[str, any]) -> Dict[str, any]:
    if "proposition_origin" not in resolution_metadata:
        return {"location": {"text": "unidentified"}}
        # return "unidentified"
    proposition_origin = resolution_metadata["proposition_origin"]
    if proposition_origin is None:
        return {"location": {"text": "unidentified"}}
        # return "unidentified"
    elif "location" in proposition_origin:
        return proposition_origin
        # if isinstance(proposition_origin["location"], dict):
        #     return {"location": proposition_origin["location"]}
        #     return proposition_origin["location"]["text"]
        # else:
        #     return {"location": proposer["location"]}
        #     return [location["text"] for location in proposition_origin["location"]]
    else:
        return {"location": {"text": "unidentified"}}
        # return "unidentified"


def clean_role(roles):
    clean_roles = []
    if isinstance(roles, str):
        roles = [roles]
    for role in roles:
        role = role.strip()
        if role.endswith(" van") or role.endswith(" uit"):
            role = role[:-4]
        if role.startswith("den ") or role.startswith("van "):
            role = role[4:]
        clean_roles.append(role)
    return clean_roles[0] if len(clean_roles) == 1 else clean_roles


def get_proposer_role(resolution_metadata):
    proposer = resolution_metadata["proposer"]
    if proposer is None:
        return "unidentified"
    elif "person_role" not in proposer:
        return "unidentified"
    if isinstance(proposer["person_role"], dict):
        return clean_role(proposer["person_role"]["text"])
    else:
        return [clean_role(role["text"]) for role in proposer["person_role"]]


def get_proposer_location(resolution_metadata: Dict[str, any]) -> Dict[str, any]:
    proposer = resolution_metadata["proposer"]
    if proposer is None:
        return {"location": {"text": "unidentified"}}
        # return "unidentified"
    elif "location" not in proposer:
        return {"location": {"text": "unidentified"}}
        # return "unidentified"
    if isinstance(proposer["location"], dict):
        return proposer["location"]
        # return proposer["location"]["text"]
    else:
        return proposer["location"]
        # return [role["text"] for role in proposer["location"]]


def get_proposer_organisation(resolution_metadata):
    proposer = resolution_metadata["proposer"]
    if proposer is None:
        return "unidentified"
    elif "organisation" not in proposer:
        return "unidentified"
    if isinstance(proposer["organisation"], dict):
        return proposer["organisation"]["text"]
    else:
        return [role["text"] for role in proposer["organisation"]]


def add_proposer_metadata(resolution, resolution_metadata):
    metadata = copy.deepcopy(resolution.metadata)
    person_loc = get_proposer_location(resolution_metadata)
    person_org = get_proposer_organisation(resolution_metadata)
    metadata["proposition_origin"] = person_loc
    metadata["proposition_organisation"] = person_org
    metadata["proposer_role"] = get_proposer_role(resolution_metadata)
    proposition_origin = get_proposition_origin(resolution_metadata)
    if proposition_origin != "unidentified":
        metadata["proposition_origin"] = proposition_origin
    for field in resolution_metadata:
        if field == "proposition_type":
            metadata["proposition_type"] = resolution_metadata["proposition_type"]
    return metadata


def add_resolution_metadata(resolution: Resolution, phrase_matches: List[PhraseMatch],
                            template_searchers: Dict[str, FuzzyTemplateSearcher],
                            variable_matchers: Dict[str, VariableMatcher]) -> Union[None, Resolution]:
    resolution = copy.deepcopy(resolution)
    opening_paragraph = resolution.paragraphs[0]
    proposition_text = get_resolution_proposition_text(resolution, phrase_matches)
    # print('proposition_text;', proposition_text)
    # for phrase_match in phrase_matches:
    #     print('\tpre-filter:', phrase_match.variant.phrase_string)
    phrase_matches = filter_matches(phrase_matches, proposition_text)
    # for phrase_match in phrase_matches:
    #     print('\tpost-filter:', phrase_match.variant.phrase_string)
    try:
        metadata = generate_resolution_metadata(phrase_matches, resolution,
                                                template_searchers, variable_matchers)
        # for key in metadata:
            # print(metadata[key])
            # for element in metadata[key]:
            #     print(element)
            #     print()
    except ValueError:
        print(f'Resolution paragraph {opening_paragraph.metadata["id"]}:\n\t', opening_paragraph.text, '\n')
        for match in phrase_matches:
            print(match.phrase.phrase_string, '\t', match.string, '\t', match.label, '\t', match.levenshtein_similarity)
        raise
        # return resolution
    # print(json.dumps(metadata, indent=4))
    if metadata:
        # evidence = [element['evidence'] for group in metadata for element in metadata[group] if 'evidence' in element]
        resolution.evidence = phrase_matches
        for metadata_group in metadata:
            group_info = {}
            for element in metadata[metadata_group]:
                label = element['element_label']
                if label in group_info:
                    if not isinstance(group_info[label], list):
                        group_info[label] = [group_info[label]]
                    group_info[label].append({
                        'text': element['phrase'],
                        'start_offset': element['start_offset'],
                        'end_offset': element['end_offset']
                    })
                else:
                    group_info[label] = {
                        'text': element['phrase'],
                        'start_offset': element['start_offset'],
                        'end_offset': element['end_offset']
                    }
            # group_info = {element['element_label']: element['phrase'] for element in metadata[metadata_group]}
            resolution.metadata[metadata_group] = group_info
    if resolution.metadata['proposition_type'] is None:
        # print('LOOKING FOR PROP TYPE')
        for phrase_match in phrase_matches:
            # print(phrase_match.phrase.metadata)
            if 'proposition_type' in phrase_match.phrase.metadata:
                resolution.metadata['proposition_type'] = phrase_match.phrase.metadata['proposition_type']
            elif phrase_match.has_label('proposition_opening'):
                for label in phrase_match.label_list:
                    if label.startswith('proposition_type'):
                        resolution.metadata['proposition_type'] = label.split(':')[1]
    resolution.metadata = add_proposer_metadata(resolution, resolution.metadata)
    # print('resolution metadata:')
    # print(json.dumps(resolution.metadata, indent=2))
    return resolution


def get_resolution_proposition_text(resolution: Resolution, phrase_matches: List[PhraseMatch]) -> str:
    proposition_end = len(resolution.paragraphs[0].text)
    phrase_matches.sort(key=lambda match: match.offset)
    min_end = 0
    opening_found: bool = False
    for pm in phrase_matches:
        if resolution.paragraphs[0].text[pm.offset:pm.end] != pm.string:
            print('invalid phrase match')
            print('first para id:', resolution.paragraphs[0].id)
            print('phrase match text id:', pm.text_id)
            continue
        # print('min_end:', min_end)
        # print(pm.variant.phrase_string, pm.string, pm.end, pm.label_list)
        if pm.has_label('proposition_opening'):
            opening_found = True
            min_end = pm.end + 5
        if pm.has_label('proposition_verb') and pm.levenshtein_similarity > 0.7 \
                and opening_found and pm.end > min_end:
            proposition_end = pm.end
            break
        if pm.has_label('resolution_decision'):
            proposition_end = pm.offset
            break
    # print('proposition_end:', proposition_end)
    proposition_text = resolution.paragraphs[0].text[:proposition_end]
    # print('proposition_text', proposition_text, '\n')
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
    return generate_template_searchers(opening_templates, phrases, searcher_config)


def generate_template_searchers(templates: List[Dict[str, any]], phrases: List[Dict[str, any]],
                                searcher_config: dict) -> Dict[str, Union[FuzzyPhraseSearcher,
                                                                          Dict[str, FuzzyTemplateSearcher],
                                                                          Dict[str, VariableMatcher]]]:
    proposition_searcher = FuzzyPhraseSearcher(searcher_config)
    proposition_phrase_model = PhraseModel(model=phrases, config=searcher_config)
    proposition_searcher.index_phrase_model(proposition_phrase_model)
    template_searchers = {}
    variable_matchers = {}
    for template in templates:
        opening_template = FuzzyTemplate(proposition_phrase_model, template)
        template_searcher = FuzzyTemplateSearcher(opening_template, searcher_config)
        template_searcher.name = template['label']
        template_searchers[template['label']] = template_searcher
        variable_matchers[template['label']] = VariableMatcher(6, 100, template_searcher.template)
    return {
        'phrase': proposition_searcher,
        'template': template_searchers,
        'variable': variable_matchers
    }
