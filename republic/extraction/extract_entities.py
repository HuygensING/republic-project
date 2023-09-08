import re
from typing import Dict, List, Set, Tuple

from fuzzy_search.tokenization.token import RegExTokenizer
from fuzzy_search.tokenization.token import Doc

from republic.helper.text_helper import TermDictionary


SINGLETON_TAG_TYPES = ['DAT', 'RES', 'PROP_OPEN', 'NON_DEC', 'NON_DEC_READ']


class Annotation:

    def __init__(self, tag_type: str, text: str, offset: int, doc_id: str = None):
        self.tag_type = tag_type
        self.text = text
        self.offset = offset
        self.end = offset + len(text)
        self.doc_id = doc_id

    def __repr__(self):
        doc_id_repr = f"'{self.doc_id}'" if self.doc_id else None
        return f"{self.__class__.__name__}(tag_type='{self.tag_type}', text='{self.text}', " \
               f"offset={self.offset}, end={self.end}, doc_id={doc_id_repr})"


class Tag:

    def __init__(self, tag_type: str, text: str, offset: int, doc_id: str = None):
        self.type = tag_type
        self.text = text
        self.offset = offset
        self.tag_string = f"<{tag_type}>{text}</{tag_type}>"
        self.end = offset + len(self.tag_string)
        self.text_end = offset + len(text)
        self.doc_id = doc_id
        self.extra_offset = len(self.tag_string) - len(self.text)

    def __repr__(self):
        doc_id_repr = f"'{self.doc_id}'" if self.doc_id else None
        return f"{self.__class__.__name__}(tag_type='{self.type}', text='{self.text}', " \
               f"offset={self.offset}, end={self.end}, doc_id={doc_id_repr})"


class TagRegExTokenizer(RegExTokenizer):

    def __init__(self, debug: int = 0, **kwargs):
        super().__init__(**kwargs)
        self.debug = debug
        # self.regex_tokenizer = RegExTokenizer(**kwargs)

    def tokenize(self, tagged_text: str, doc_id: str = None, debug: int = None) -> Doc:
        if debug is None:
            debug = self.debug
        clean_text, annotations = transform_tags_to_standoff(tagged_text, debug=debug)
        if self.debug > 0:
            print('tokeinze - num annotations:', len(annotations))
            print('\ntokenize - clean_text:', clean_text)
        doc = super().tokenize(clean_text, doc_id=doc_id)
        if self.include_boundary_tokens:
            for anno in annotations:
                # adjust offset with width of <START> boundary token and whitespace
                anno.offset += 8
                anno.end += 8
        for token in doc:
            if len(annotations) == 0:
                break
            curr_anno = annotations[0]
            if self.debug > 0:
                print('tokeinze - curr_anno:', curr_anno)
                print('tokeinze - curr_token:', token.char_index, token.i, token.n)
            if curr_anno.offset <= token.char_index < curr_anno.end:
                token.metadata['tag_type'] = curr_anno.tag_type
                token.metadata['tag_text'] = curr_anno.text
                token.metadata['tag_offset'] = curr_anno.offset
                token.metadata['tag_end'] = curr_anno.end
            elif token.char_index >= curr_anno.end:
                annotations.pop(0)
                if self.debug > 0:
                    print('tokeinze - popping - num annotations:', len(annotations))
            if self.debug > 0:
                print(token.metadata)
        return doc


def extract_non_tagged_strings(tagged_text, doc_id: str = None, debug: int = 0):
    tags = extract_tags(tagged_text)
    remaining_text = tagged_text
    non_tagged_strings = []
    if debug > 0:
        print(tagged_text, '\n\n')
    for tag in sorted(tags, key=lambda t: t.end, reverse=True):
        non_tagged_string = remaining_text[tag.end:]
        if debug > 0:
            print('non_tagged_string:', non_tagged_string)
        non_tagged_strings.append({
            'doc_id': doc_id,
            'text': non_tagged_string,
            'offset': tag.end,
            'end': tag.end + len(non_tagged_string)
        })
        remaining_text = remaining_text[:tag.offset]
        if debug > 0:
            print('remaining_text:', remaining_text)
            print()
    if len(remaining_text) > 0:
        non_tagged_strings.append({
            'doc_id': doc_id,
            'text': remaining_text,
            'offset': 0,
            'end': len(remaining_text)
        })
    return non_tagged_strings[::-1]


def transform_tags_to_standoff(tagged_text: str, doc_id: str = None, debug: int = 0):
    tags = extract_tags(tagged_text, doc_id=doc_id)
    clean_text = tagged_text
    annos = []
    if debug > 0:
        print(tagged_text)
        print('num tags:', len(tags))
        print()
    extra_tag_offset = sum([tag.extra_offset for tag in tags])
    for ti, tag in enumerate(tags[::-1]):
        num_preceeding = len(tags) - (ti+1)
        if debug > 0:
            print('num_preceeding:', num_preceeding)
        extra_tag_offset = extra_tag_offset - tag.extra_offset
        if debug > 0:
            print('extra_tag_offset:', extra_tag_offset)
        anno = Annotation(tag.type, tag.text, tag.offset - extra_tag_offset, doc_id=tag.doc_id)
        if debug > 0:
            print('tag offset:', tag.offset)
            print('tag end:', tag.end)
            print('tag len:', len(tag.tag_string))
        annos.append(anno)
        if debug > 0:
            print(clean_text[:tag.offset])
            print(tag.text)
            print(clean_text[tag.end:])
        clean_text = clean_text[:tag.offset] + tag.text + clean_text[tag.end:]
        if debug > 0:
            print()
    for anno in annos:
        if debug > 0:
            print(anno.text)
            print(clean_text[anno.offset:anno.end])
        message = f'tag text and anno range text are not aligned:' \
                  f'\n\ttag text: {anno.text}' \
                  f'\n\tanno range text: {clean_text[anno.offset:anno.end]}'
        assert clean_text[anno.offset:anno.end] == anno.text, IndexError(message)
    return clean_text, annos[::-1]


def extract_tags(tagged_text: str, doc_id: str = None) -> List[Tag]:
    tags = []
    for m in re.finditer(r'<([A-Z_]{3,})>(.*?)</\1>', tagged_text):
        tag_type = m.group(1)
        tag_text = m.group(2)
        tag_offset = m.start()
        tag = Tag(tag_type, tag_text, tag_offset, doc_id=doc_id)
        tags.append(tag)
    return tags


def extract_tag_sequences(tagged_text, doc_id: str = None, debug: int = 0):
    tags = extract_tags(tagged_text, doc_id=doc_id)
    if debug > 0:
        print('extract_tag_sequences - tags:', len(tags))
    prev_end = 0
    if len(tags) == 0:
        return None
    elif len(tags) == 1:
        yield tags
        return None
    sequence = []
    for tag in tags:
        if tag.offset - prev_end > 2:
            if len(sequence) > 0:
                yield sequence
            sequence = []
        if tag.type in SINGLETON_TAG_TYPES:
            if len(sequence) > 0:
                yield sequence
            yield [tag]
            sequence = []
        elif len(sequence) > 0 and sequence[-1].type.startswith('DEC') and tag.type.startswith('DEC') is False:
            if len(sequence) > 0:
                yield sequence
            sequence = [tag]
        elif len(sequence) > 0 and sequence[-1].type.startswith('DEC') is False and tag.type.startswith('DEC'):
            if len(sequence) > 0:
                yield sequence
            sequence = [tag]
        else:
            sequence.append(tag)
        prev_end = tag.end
    if len(sequence) > 0:
        yield sequence
    return None


def get_sequence_main_tag(sequence: List[Tag]):
    if len(sequence) == 1:
        if sequence[0].type == 'HOE':
            return 'PER'
        else:
            return sequence[0].type
    for tag in sequence:
        if tag.type in {'PER', 'ORG', 'COM'}:
            return tag.type
        elif tag.type.startswith('DEC'):
            return tag.type
        elif tag.type.startswith('PROP'):
            return tag.type
        else:
            return tag.type
            # continue
    return sequence[0].type


def replace_tags(tagged_text: str, tags: List[Dict[str, any]]) -> str:
    for tag in tags:
        tagged_text = tagged_text.replace(tag['tag_string'], f"<{tag['type']}/>", 1)
    return tagged_text
    # return text.replace('><', '> <').replace('>,', '> ,')


def get_phrase_term_labels(geo_name: str, term_dict: TermDictionary,
                           leaf_cats_only: bool = False) -> List[Set[str]]:
    geo_terms = geo_name.split(' ')
    labels = [term_dict.get_term_cats(term) if term_dict.has_term(term) else None for term in geo_terms]
    if leaf_cats_only:
        leaf_labels = []
        for label_set in labels:
            leaf_set = {label for label in label_set if label in term_dict.leaf_cats}
            leaf_labels.append(leaf_set)
        labels = leaf_labels
    return labels


def geo_name_has_hierarchical_signal(geo_name: str) -> bool:
    if ' in ' in geo_name or ' op ' in geo_name:
        return True
    else:
        return False


def geo_name_has_article_prefix(geo_name: str, term_dict: TermDictionary) -> bool:
    geo_terms = geo_name.split(' ')
    if term_dict.has_term(geo_terms[0]) and \
            "function_article" in term_dict.get_term_cats(geo_terms[0]):
        return True
    else:
        return False


def geo_name_has_reference_prefix(geo_name: str, term_dict: TermDictionary) -> bool:
    geo_terms = geo_name.split(' ')
    if term_dict.has_term(geo_terms[0]) and \
            "meeting_reference" in term_dict.get_term_cats(geo_terms[0]):
        return True
    else:
        return False


def geo_name_has_type_prefix(geo_name: str, term_dict: TermDictionary) -> bool:
    geo_terms = geo_name.split(' ')
    if term_dict.has_term(geo_terms[0]) and \
            "location" in term_dict.get_term_cats(geo_terms[0]):
        return True
    else:
        return False


def geo_name_has_vehicle_prefix(geo_name: str, term_dict: TermDictionary) -> bool:
    geo_terms = geo_name.split(' ')
    if term_dict.has_term(geo_terms[0]) and \
            "object_vehicle" in term_dict.get_term_cats(geo_terms[0]):
        return True
    else:
        return False


def geo_name_has_dependence_prefix(geo_name: str) -> bool:
    geo_terms = geo_name.split(' ')
    if geo_terms[0] in {'van', 'te', 'tot', 'ter'}:
        return True
    if geo_terms[0] == 'van' or geo_terms[0] == 'te':
        return True
    else:
        return False


def geo_name_has_sequence(geo_name: str) -> bool:
    geo_terms = geo_name.split(' ')
    for geo_term in geo_terms:
        if len(geo_term) > 0 and geo_term[0] == ',':
            return True
    else:
        return False


def is_geo_term(geo_name: str, term_dict: TermDictionary) -> bool:
    for geo_term in geo_name.split(' '):
        if not term_dict.has_term(geo_term):
            continue
        if "location_region" in term_dict.get_term_cats(geo_term) or "geographical_name" in term_dict.get_term_cats(
                geo_term):
            return True
    return False


def geo_name_has_type(geo_name: str, term_dict: TermDictionary) -> bool:
    # geo_term_labels = [term_dict.get_term_cats(term) if term_dict.has_term(term) else None for term in geo_terms]
    if "location_region" in term_dict.get_term_cats(geo_name):
        return True
    for geo_term in geo_name.split(' '):
        if not term_dict.has_term(geo_term):
            continue
        if "location_region" in term_dict.get_term_cats(geo_term):
            return True
    return False


def geo_name_has_organisation(geo_name: str, term_dict: TermDictionary) -> bool:
    # geo_term_labels = [term_dict.get_term_cats(term) if term_dict.has_term(term) else None for term in geo_terms]
    for geo_term in geo_name.split(' '):
        if not term_dict.has_term(geo_term):
            continue
        if "organisation" in term_dict.get_term_cats(geo_term):
            print(geo_term, term_dict.get_term_cats(geo_term))
            return True
    return False


def get_geo_name_cat(geo_name: str, term_dict: TermDictionary) -> Set[str]:
    geo_terms = geo_name.split(' ')
    geo_types = set()
    if "geographical_name" in term_dict.get_term_cats(geo_name):
        for cat in term_dict.get_term_cats(geo_name):
            if cat.startswith("geographical_name_"):
                geo_types.add(cat)
    for geo_term in geo_terms:
        if not term_dict.has_term(geo_term):
            continue
        if "geographical_name" in term_dict.get_term_cats(geo_term):
            for cat in term_dict.get_term_cats(geo_term):
                if cat.startswith("geographical_name_"):
                    geo_types.add(cat)
    return geo_types


def get_geo_name_organisation(geo_name: str, term_dict: TermDictionary) -> Set[str]:
    geo_terms = geo_name.split(' ')
    geo_types = set()
    if "organisation" in term_dict.get_term_cats(geo_name):
        for cat in term_dict.get_term_cats(geo_name):
            if cat.startswith("organisation_"):
                geo_types.add(cat)
    for geo_term in geo_terms:
        if term_dict.has_term(geo_term) and "organisation" in term_dict.get_term_cats(geo_term):
            for cat in term_dict.get_term_cats(geo_term):
                if cat.startswith("organisation_"):
                    geo_types.add(cat)
    return geo_types


def get_geo_name_location_type(geo_name: str, term_dict: TermDictionary) -> Set[str]:
    geo_terms = geo_name.split(' ')
    geo_types = set()
    if "location" in term_dict.get_term_cats(geo_name):
        for cat in term_dict.get_term_cats(geo_name):
            if cat.startswith("location_"):
                geo_types.add(cat)
    for geo_term in geo_terms:
        if term_dict.has_term(geo_term) and "location" in term_dict.get_term_cats(geo_term):
            for cat in term_dict.get_term_cats(geo_term):
                if cat.startswith("location_"):
                    geo_types.add(cat)
    return geo_types


def init_parsed_name(geo_name: str) -> Dict[str, any]:
    return {
        "full_string": geo_name,
        "type": set(),
        "terms": geo_name.split(' ')
    }


def parse_geo_article_prefix_name(geo_name: str,
                                  term_dict: TermDictionary) -> Dict[str, any]:
    geo_terms = geo_name.split(' ')
    if "function_article" not in term_dict.get_term_cats(geo_terms[0]):
        raise ValueError(f"geo_name {geo_name} does not start with a known article")
    geo_name = ' '.join(geo_terms[1:])
    parsed_name = parse_geo_name(geo_name, term_dict)
    parsed_name["article_prefix"] = geo_terms[0]
    return parsed_name


def parse_geo_reference_prefix_name(geo_name: str,
                                    term_dict: TermDictionary) -> Dict[str, any]:
    geo_terms = geo_name.split(' ')
    if "meeting_reference" not in term_dict.get_term_cats(geo_terms[0]):
        raise ValueError(f"geo_name {geo_name} does not start with a known meeting reference")
    geo_name = ' '.join(geo_terms[1:])
    parsed_name = parse_geo_name(geo_name, term_dict)
    parsed_name["reference"] = geo_terms[0]
    return parsed_name


def parse_geo_vehicle_prefix_name(geo_name: str,
                                  term_dict: TermDictionary) -> Dict[str, any]:
    geo_terms = geo_name.split(' ')
    if "object_vehicle" not in term_dict.get_term_cats(geo_terms[0]):
        raise ValueError(f"geo_name {geo_name} does not start with a known vehicle type name")
    geo_name = ' '.join(geo_terms[1:])
    parsed_name = parse_geo_name(geo_name, term_dict)
    parsed_name["vehicle"] = geo_terms[0]
    return parsed_name


def parse_geo_type_prefix_name(geo_name: str, term_dict: TermDictionary) -> Dict[str, any]:
    geo_terms = geo_name.split(' ')
    if "location" not in term_dict.get_term_cats(geo_terms[0]):
        raise ValueError(f"geo_name '{geo_name}' does not start with a known location type term")
    geo_name = ' '.join(geo_terms[1:])
    if len(geo_terms) == 0:
        parsed_name = init_parsed_name(geo_name)
    else:
        parsed_name = parse_geo_name(geo_name, term_dict)
    parsed_name["type"].add(geo_terms[0])
    for type_cat in get_geo_name_location_type(geo_terms[0], term_dict):
        parsed_name["type"].add(type_cat)
    return parsed_name


def parse_geo_dependence_prefix_name(geo_name: str, term_dict: TermDictionary) -> Dict[str, any]:
    geo_terms = geo_name.split(' ')
    if geo_terms[0] not in {'van', 'te'}:
        raise ValueError(f"geo_name '{geo_name}' does not start with a known dependence term")
    parsed_name = init_parsed_name(geo_name)
    parsed_name["type_relation"] = geo_terms.pop(0)
    parsed_name["dependent_of"] = parse_geo_name(' '.join(geo_terms), term_dict)
    return parsed_name


def parse_geo_sequence_name(geo_name: str, term_dict: TermDictionary) -> Dict[str, any]:
    if ',' not in geo_name and ' en ' not in geo_name:
        raise ValueError(f"geo_name '{geo_name}' has no sequence symbols (',', ' en ')")

    geo_terms = [geo_term.strip() for geo_term in geo_name.replace(' en ', ', ').split(',')]
    parsed_name = init_parsed_name(geo_name)
    parsed_name["sequence"] = [parse_geo_name(geo_term, term_dict) for geo_term in geo_terms]
    return parsed_name


def parse_geo_organisation_name(geo_name: str, term_dict: TermDictionary) -> Dict[str, any]:
    parsed_name = init_parsed_name(geo_name)
    geo_terms = geo_name.split(' ')
    if "organisation_prefix" in term_dict.get_term_cats(geo_terms[0]):
        if len(geo_terms) >= 2 and "organisation" in term_dict.get_term_cats(geo_terms[1]):
            parsed_name["type"].add(' '.join(geo_terms[:2]))
            for org_type in get_geo_name_organisation(geo_terms[1], term_dict):
                parsed_name["type"].add(org_type)
            geo_terms = geo_terms[:2]
        else:
            for org_type in get_geo_name_organisation(geo_terms[0], term_dict):
                parsed_name["type"].add(org_type)
            parsed_name["organisation_prefix"] = geo_terms.pop(0)
    for geo_term in geo_terms:
        # parsed all location_region terms
        if "organisation" in term_dict.get_term_cats(geo_term):
            parsed_name["type"].add(geo_terms.pop(0))
            for org_type in get_geo_name_organisation(geo_term, term_dict):
                parsed_name["type"].add(org_type)
    if len(geo_terms) == 0:
        return parsed_name
    if geo_terms[0] == 'van' or geo_terms[0] == 'te':
        parsed_name["type_relation"] = geo_terms.pop(0)
        parsed_name["dependent_of"] = parse_geo_name(' '.join(geo_terms), term_dict)
    else:
        for geo_term in geo_terms:
            parsed_name["terms"].append({"string": geo_term, "type": get_geo_name_organisation(geo_term, term_dict)})
    return parsed_name


def parse_geo_hierarchical_name(geo_name: str, term_dict: TermDictionary) -> Dict[str, any]:
    if ' in ' in geo_name:
        geo_parts = geo_name.split(' in ')
    elif ' op ' in geo_name:
        geo_parts = geo_name.split(' op ')
    else:
        raise ValueError(f"geo_name '{geo_name}' has no hierarchical relation")
    parsed_geo_names = [parse_geo_name(geo_part, term_dict) for geo_part in geo_parts]
    for smaller_geo in parsed_geo_names[:-1]:
        larger_geo = parsed_geo_names[parsed_geo_names.index(smaller_geo) + 1]
        smaller_geo["part_of"] = larger_geo
    return parsed_geo_names[0]


def is_known_geo_name(geo_name: str, term_dict: TermDictionary) -> bool:
    if term_dict.has_term(geo_name) is False:
        return False
    return "geographical_name" in term_dict.get_term_cats(geo_name)


def find_similar_geo_names(geo_name: str,
                           term_dict: TermDictionary, min_sim_score: float = 0.6) -> List[str]:
    selected_terms = []
    sim_terms = term_dict.skip_sim.rank_similar(geo_name)
    for sim_term, sim_score in sim_terms:
        if "geographical_name" not in term_dict.get_term_cats(sim_term):
            continue
        if sim_score < min_sim_score:
            continue
        selected_terms.append(sim_term)
        print('\t', sim_term, sim_score)
    return selected_terms


def parse_geo_plain_name(geo_name: str, term_dict: TermDictionary) -> Dict[str, any]:
    # print('\tadding remaining terms:', geo_name, term_dict.has_term(geo_name))
    parsed_name = {
        "full_string": geo_name,
        "type": get_geo_name_cat(geo_name, term_dict),
        "terms": geo_name.split(' ')
    }
    if not term_dict.has_term(geo_name):
        sim_terms = find_similar_geo_names(geo_name, term_dict)
        if len(sim_terms) > 0:
            parsed_name["similar_names"] = sim_terms
    return parsed_name


def parse_geo_name(geo_name: str, term_dict: TermDictionary) -> Dict[str, any]:
    if is_known_geo_name(geo_name, term_dict) is False:
        if geo_name_has_hierarchical_signal(geo_name):
            return parse_geo_hierarchical_name(geo_name, term_dict)
        elif geo_name_has_dependence_prefix(geo_name):
            return parse_geo_dependence_prefix_name(geo_name, term_dict)
        elif geo_name_has_article_prefix(geo_name, term_dict):
            return parse_geo_article_prefix_name(geo_name, term_dict)
        elif geo_name_has_reference_prefix(geo_name, term_dict):
            return parse_geo_reference_prefix_name(geo_name, term_dict)
        elif geo_name_has_vehicle_prefix(geo_name, term_dict):
            return parse_geo_vehicle_prefix_name(geo_name, term_dict)
        elif geo_name_has_type_prefix(geo_name, term_dict):
            return parse_geo_type_prefix_name(geo_name, term_dict)
        elif geo_name_has_organisation(geo_name, term_dict):
            return parse_geo_organisation_name(geo_name, term_dict)
        elif geo_name_has_sequence(geo_name):
            return parse_geo_sequence_name(geo_name, term_dict)
    return parse_geo_plain_name(geo_name, term_dict)
