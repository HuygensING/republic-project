from typing import Dict, List, Set, Tuple

from republic.helper.text_helper import TermDictionary


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
