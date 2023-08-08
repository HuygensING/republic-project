import gzip
import os
import pickle
import time

from fuzzy_search.search.phrase_searcher import FuzzyPhraseSearcher
from fuzzy_search.match.phrase_match import PhraseMatch

import republic.extraction.extract_entities as extract
from republic.helper.utils import get_project_dir
from republic.extraction.extract_entities import Tag
from republic.model.resolution_phrase_model import proposition_opening_phrases
from republic.nlp.read import read_paragraphs


FORMULAS = [
    {
        'phrase': 'gesonden sal werden aen',
        'variants': [
            'gesonden sullen werden aen',
            'gesonden werden aen'
        ],
        'label': ['decision', 'decision:send']
    },
    {
        'phrase': 'gestelt sal werden in handen van',
        'variants': [
            'gestelt sullen werden in handen van'
        ],
        'label': ['decision', 'decision:hand_to']
    },
    {
        'phrase': 'WAAR op geen resolutie is gevallen',
        'label': ['no_decision']
    },
    {
        'phrase': 'zyn deselve gehouden voor gelesen',
        'label': ['no_decision', 'no_decision:read']
    },
    {
        'phrase': 'WAER op gedelibereert zynde',
        'label': ['decision', 'decision:deliberation'],
        'variants': [
            'waer op gedelibereert zynde',
        ]
    },
    {
        'phrase': 'IS na voorgaende deliberatie goetgevonden ende verstaen',
        'label': ['decision', 'decision:deliberation_accepted'],
        'variants': [
            'is na deliberatie goetgevonden en verstaen'
        ]
    },
    {
        'phrase': 'is goetgevonden ende verstaen',
        'label': ['decision', 'decision:accepted']
    },
    {
        'phrase': 'dat Copie van de voorschreve',
        'variants': [
            'dat Copie van voorschr'
        ],
        'label': ['decision', 'decision:copy']
    },
    {
        'phrase': 'ende van alles alhier ter Vergadeninge rapport te doen',
        'label': ['decision', 'decision:report']
    },
    {
        'phrase': 'te nomineren, te visiteren examineren',
        'label': ['decision', 'decision:examine'],
        'variants': [
            'te visiteren examineren',
            'te visiteren examineren en liquideren'
        ]
    },
]


LABEL_TAG = {
    'decision': 'DEC',
    'decision:accepted': 'DEC_ACC',
    'decision:copy': 'DEC_COPY',
    'decision:deliberation': 'DEC_DEL',
    'decision:deliberation_accepted': 'DEC_DEL_ACC',
    'decision:hand_to': 'DEC_HAND',
    'decision:send': 'DEC_SEND',
    'no_decision': 'NON_DEC',
    'no_decision:read': 'NON_DEC_READ',
    'proposition_opening': 'PROP_OPEN',
    'decision:report': 'DEC_REPO',
    'decision:examine': 'DEC_EXAM',
}


def read_metadata(res_metadata_file):
    with open(res_metadata_file, 'rb') as fh:
        res_metadata = pickle.load(fh)
    return res_metadata


def get_res_prop_type():
    project_dir = get_project_dir()
    res_metadata_file = os.path.join(project_dir, 'data/metadata/resolution_proposition_metadata-loghi.pcl')
    res_prop_meta = read_metadata(res_metadata_file)
    return res_prop_meta['type']


def filter_overlapping_tags(tags):
    if len(tags) < 2:
        return tags
    curr_tag = tags[0]
    filtered_tags = []
    for next_tag in tags[1:]:
        if curr_tag.text_end < next_tag.offset:
            # print('\tno overlap, adding curr_tag')
            filtered_tags.append(curr_tag)
            curr_tag = next_tag
        elif len(curr_tag.text) > len(next_tag.text):
            # print('curr_tag:', curr_tag)
            # print('next_tag:', next_tag)
            # print('\toverlap, curr is longer, keeping curr')
            continue
        else:
            # print('curr_tag:', curr_tag)
            # print('next_tag:', next_tag)
            # print('\toverlap, next is longer, switching to next')
            curr_tag = next_tag
    if curr_tag not in filtered_tags:
        filtered_tags.append(curr_tag)
    return filtered_tags


def get_match_tag(match: PhraseMatch) -> str:
    best_tag = ''
    for label in match.label:
        if label not in LABEL_TAG:
            continue
        if len(LABEL_TAG[label]) > len(best_tag):
            best_tag = LABEL_TAG[label]
    return best_tag if len(best_tag) > 0 else None


def make_searcher():
    config = {
        'levenshtein_threshold': 0.8,
        'include_variants': True,
        'ngram_size': 3,
        'skip_size': 1
    }
    all_phrases = FORMULAS + proposition_opening_phrases
    return FuzzyPhraseSearcher(phrase_model=all_phrases, config=config)


def tag_inventory_formulas(inv_num: str, debug: int = 0):
    searcher = make_searcher()
    project_dir = get_project_dir()
    tagged_dir = os.path.join(project_dir, 'data/resolutions/ner_tagged')
    tagged_extra_dir = os.path.join(project_dir, 'data/resolutions/ner_tagged_extra')
    tagged_file = os.path.join(tagged_dir, f"resolutions-{inv_num}.tsv.gz")
    extra_tagged_file = os.path.join(tagged_extra_dir, f'resolutions-extra_tagged-{inv_num}.tsv.gz')
    start = time.time()
    has_prop_type = get_res_prop_type()
    with gzip.open(extra_tagged_file, 'wt') as fh:

        res_count = 0
        match_count = 0
        for res_id, res_text in read_paragraphs(tagged_file):
            res_count += 1
            if res_id not in has_prop_type:
                continue
            non_tagged_strings = extract.extract_non_tagged_strings(res_text, res_id)
            new_tags = []
            for non_tagged_string in non_tagged_strings:
                if len(non_tagged_string['text']) < 10:
                    continue
                if debug > 1:
                    print(non_tagged_string)
                non_tagged_string['text_id'] = res_id
                non_tagged_string['id'] = res_id
                matches = searcher.find_matches(non_tagged_string, debug=0)
                match_count += len(matches)
                for match in matches:
                    offset = match.offset + non_tagged_string['offset']
                    end = offset + len(match.string)
                    if debug > 1:
                        print('\t', match.string)
                        print('\t', match.label)
                        print('\t', get_match_tag(match))
                        print('\t', res_text[offset:end])
                        print(match.json())
                        print()
                    match_tag = get_match_tag(match)
                    tag = Tag(tag_type=match_tag, text=match.string, offset=offset, doc_id=res_id)
                    new_tags.append(tag)
                if debug > 1:
                    print('\n')
            if debug > 1:
                print(new_tags)
            filtered_tags = filter_overlapping_tags(new_tags)
            if debug > 1:
                if len(filtered_tags) < len(new_tags):
                    for new_tag in new_tags:
                        print('NEW:', new_tag)
                    for filtered_tag in filtered_tags:
                        print('FILTERED:', filtered_tag)
            for tag in filtered_tags[::-1]:
                res_text_range = res_text[tag.offset:tag.offset + len(tag.text)]
                if tag.text != res_text_range:
                    print(new_tags)
                    print(tag.offset, len(tag.text))
                    print(f'TEXT: {res_text}\n')
                    print('PREFIX:', res_text[:tag.offset])
                    print('TAG_STRING:', tag.text)
                    print('SUFFIX:', res_text[tag.offset + len(tag.text):])
                    print()
                    print('COMBINED:', res_text[:tag.offset] + tag.tag_string + res_text[tag.offset + len(tag.text):])
                    print('\n')
                message = f'tag.text and range in res_text are not aligned: \n\t{tag.text}\n\t{res_text_range}'
                assert tag.text == res_text_range, ValueError(message)
                res_text = res_text[:tag.offset] + tag.tag_string + res_text[tag.offset + len(tag.text):]
            fh.write(f"{res_id}\t{res_text}\n")
            if res_count % 1000 == 0:
                step = time.time()
                took = step - start
                if debug > 0:
                    print(f"{res_count}\ttook: {took: >8.0f} seconds")
        print(f"{res_count}\ttook: {took: >8.0f} seconds")

    print('number of matches:', match_count)

