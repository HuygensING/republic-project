from typing import Union, Dict, List
from elasticsearch import Elasticsearch
import republic.elastic.republic_elasticsearch as rep_es


def find_index_page_sequence(es: Elasticsearch, inventory_num: int, config: dict) -> Dict[str, int]:
    index_pages = rep_es.retrieve_index_pages(es, inventory_num, config)
    pages = sorted([index_page["page_num"] for index_page in index_pages])
    return find_sequence(pages)


def find_resolution_page_sequence(es: Elasticsearch, inventory_num: int, config: dict) -> Dict[str, int]:
    resolution_pages = rep_es.retrieve_resolution_pages(es, inventory_num, config)
    pages = sorted([resolution_page["page_num"] for resolution_page in resolution_pages])
    return find_sequence(pages)


def find_respect_page_sequence(es: Elasticsearch, inventory_num: int, config: dict) -> Dict[str, int]:
    respect_pages = rep_es.retrieve_respect_pages(es, inventory_num, config)
    pages = sorted([respect_page["page_num"] for respect_page in respect_pages])
    return find_sequence(pages)


def find_page_type_sequences(es: Elasticsearch, inventory_num: int, config: dict) -> list:
    page_types = ["index_page", "resolution_page", "respect_page"]
    page_type_sequences = []
    for page_type in page_types:
        pages = rep_es.retrieve_pages_by_type(es, page_type, inventory_num, config)
        if len(pages) == 0:
            continue # skip types that have no pages
        page_nums = sorted([page["page_num"] for page in pages])
        #print(page_type, "page_nums:", page_nums)
        page_type_sequence = find_sequence(page_nums)
        #print(page_type, page_type_sequence)
        page_type_sequence["page_type"] = page_type
        page_type_sequences += [page_type_sequence]
    return page_type_sequences


def find_sequence(pages: List[int]) -> Dict[str, int]:
    longest_sequence = []
    longest_sequence_length = 0
    sequence = [pages[0]]
    for curr_page in pages[1:]:
        if curr_page - sequence[-1] < 20:
            sequence += [curr_page]
        else:
            if len(sequence) > longest_sequence_length:
                longest_sequence_length = len(sequence)
                longest_sequence = sequence
            sequence = [curr_page]
    if len(sequence) > longest_sequence_length:
        longest_sequence = sequence
    return {"start": longest_sequence[0], "end": longest_sequence[-1]}


def find_pages_with_little_text(es: Elasticsearch, word_num_threshold: int, inventory_num: int, config: dict) -> list:
    match_fields = [
        {"range": {"num_words": {"lte": word_num_threshold}}},
        {"match": {"inventory_num": inventory_num}}
    ]
    query = rep_es.make_bool_query(match_fields)
    return rep_es.retrieve_pages_with_query(es, query, config)


def find_page_type_order(es: Elasticsearch, inventory_num: int, config: dict) -> Dict[
    str, Union[Dict[str, int], List[str]]]:
    index_sequence = find_index_page_sequence(es, inventory_num, config)
    resolution_sequence = find_resolution_page_sequence(es, inventory_num, config)
    if resolution_sequence["end"] - resolution_sequence["start"] < 200:
        raise ValueError("Improbable resolution sequence length")
    if index_sequence["end"] < resolution_sequence["start"]:
        page_type_order = ["index_page", "resolution_page"]
    elif resolution_sequence["end"] < index_sequence["start"]:
        page_type_order = ["resolution_page", "index_page"]
    elif resolution_sequence["end"] < index_sequence["end"]:
        page_type_order = ["resolution_page", "index_page"]
    elif index_sequence["start"] < resolution_sequence["start"]:
        page_type_order = ["index_page", "resolution_page"]
    else:
        print("inventory number:", inventory_num, "\tindex page sequence:", index_sequence)
        print("inventory number:", inventory_num, "\tresolution page sequence:", resolution_sequence)
        raise ValueError("Impossible resolution and index page sequences")
    return {
        "index_sequence": index_sequence,
        "resolution_sequence": resolution_sequence,
        "page_type_order": page_type_order
    }


def get_inventory_num_pages(es: Elasticsearch, inventory_num: int, config: dict) -> int:
    query = {"query": {"match": {"inventory_num": inventory_num}}, "size": 10000}
    pages = rep_es.retrieve_pages_with_query(es, query, config)
    return len(pages)


def find_page_type_sections(inventory_data: dict) -> list:
    sections = []
    for title_index, title_page in enumerate(inventory_data["title_pages"]):
        if title_page["num_words"] < 100 and "single_column" in title_page["page_type"]:
            continue
        section = {"start": title_page["page_num"], "end": inventory_data["num_pages"]}
        if len(inventory_data["title_pages"]) > title_index + 1:
            section["end"] = inventory_data["title_pages"][title_index + 1]["page_num"] - 1
        section["page_type"] = find_page_type_sequence_overlap(inventory_data, section)
        sections += [section]
    return sections


def section_sequence_overlap(section: dict, sequence: dict) -> Union[int, None]:
    overlap_start = max([section["start"], sequence["start"]])
    overlap_end = min([section["end"], sequence["end"]])
    if overlap_end < overlap_start:
        return None
    return overlap_end - overlap_start


def find_page_type_sequence_overlap(inventory_data: dict, section: dict) -> str:
    largest_overlap = -1
    largest_overlap_type = "unknown_page_type"
    largest_sequence = None
    for page_type_sequence in inventory_data["page_type_sequences"]:
        #print(page_type_sequence, section)
        sequence_length = page_type_sequence["end"] - page_type_sequence["start"]
        overlap = section_sequence_overlap(section, page_type_sequence)
        if overlap and overlap == largest_overlap:
            #print("choose smallest sequence page_type")
            if sequence_length < largest_sequence:
                largest_overlap_type = page_type_sequence["page_type"]
                largest_sequence = sequence_length
        if overlap and overlap > largest_overlap:
            largest_overlap = overlap
            largest_overlap_type = page_type_sequence["page_type"]
            largest_sequence = sequence_length

    return largest_overlap_type


def get_inventory_summary(es: Elasticsearch, inventory_config: dict) -> dict:
    inventory_num = inventory_config["inventory_num"]
    inventory_data = {}
    title_pages = rep_es.retrieve_title_pages(es, inventory_num, inventory_config)
    title_pages.sort(key= lambda x: x["page_num"])
    inventory_data["title_pages"] = title_pages
    inventory_data["title_page_nums"] = [title_page["page_num"] for title_page in title_pages]
    inventory_data["num_pages"] = get_inventory_num_pages(es, inventory_num, inventory_config)
    inventory_data["page_type_sequences"] = find_page_type_sequences(es, inventory_num, inventory_config)
    inventory_data["sections"] = find_page_type_sections(inventory_data)
    #inventory_data["page_type_sequences"] = page_type_sequences
    return inventory_data


def add_inventory_metadata(metadata: dict, inventory_data: dict, config: dict) -> dict:
    metadata["year"] = config["year"]
    metadata["num_pages"] = inventory_data["num_pages"]
    metadata["title_page_nums"] = inventory_data["title_page_nums"]
    metadata["sections"] = find_page_type_sections(inventory_data)
    add_type_page_num_offsets(metadata)
    return metadata


def add_type_page_num_offsets(metadata: dict):
    type_page_num_offsets = {}
    for section in metadata["sections"]:
        if section["page_type"] not in type_page_num_offsets:
            type_page_num_offsets[section["page_type"]] = section["start"]
        elif section["start"] < type_page_num_offsets[section["page_type"]]:
            type_page_num_offsets[section["page_type"]] = section["start"]
    metadata["type_page_num_offsets"] = []
    for page_type in type_page_num_offsets:
        page_num_offset = type_page_num_offsets[page_type]
        metadata["type_page_num_offsets"] += [{"page_type": page_type,
                                               "page_num_offset": page_num_offset}]


def make_inventory_metadata_doc(es: Elasticsearch, inventory_num: int, inventory_data: dict,
                                config: dict) -> dict:
    if es.exists(index=config["inventory_index"],
                 doc_type=config["inventory_doc_type"], id=inventory_num):
        response = es.get(index=config["inventory_index"],
                               doc_type=config["inventory_doc_type"], id=inventory_num)
        metadata = response["_source"]
    else:
        metadata = {"inventory_num": inventory_num}
    metadata = add_inventory_metadata(metadata, inventory_data, config)
    return metadata


