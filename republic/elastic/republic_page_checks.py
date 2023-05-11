from typing import List

from elasticsearch import Elasticsearch
import pagexml.model.physical_document_model as pdm

from republic.elastic.republic_elasticsearch import initialize_es
from republic.elastic.republic_elasticsearch import RepublicElasticsearch as RepEs
import republic.analyser.republic_inventory_analyser as inv_analyser


def score_levenshtein_distance(s1: str, s2: str) -> int:
    if len(s1) > len(s2):
        s1, s2 = s2, s1
    distances = range(len(s1) + 1)
    for i2, c2 in enumerate(s2):
        distances_ = [i2 + 1]
        for i1, c1 in enumerate(s1):
            if c1 == c2:
                distances_.append(distances[i1])
            else:
                distances_.append(1 + min((distances[i1], distances[i1 + 1], distances_[-1])))
        distances = distances_
    return distances[-1]


###########################################################################
# Correcting page types
#
# **Problem 1**: For some pages the page type may be incorrectly identified (e.g. an index
# page identified as a resolution page or vice versa). This mainly happens on pages with
# little text content or pages where the columns are misidentified.
#
# **Solution**: Using the title pages as part separators, and knowing that the indices
# precede the resolution pages, we can identify misclassified page and correct their labels.
#
###########################################################################


def filter_page_type(page_doc: dict) -> List[str]:
    filtered = []
    for page_type in page_doc["page_type"]:
        if "index_" in page_type:
            continue
        if "respect_" in page_type:
            continue
        if "resolution_" in page_type:
            continue
        filtered += [page_type]
    return filtered


def swap_page_type(page_doc: dict, new_page_type: str) -> List[str]:
    page_type = filter_page_type(page_doc)
    page_type += [new_page_type]
    return page_type


def in_section(page_num: int, section_type: str, inventory_info: dict) -> bool:
    if section_type not in inventory_info:
        return False
    return inventory_info[section_type]["from"] <= page_num <= inventory_info[section_type]["to"]


def has_correct_page_type(page_doc: dict, inventory_info: dict) -> bool:
    if in_section(page_doc["page_num"], "respect_page", inventory_info):
        return "respect_page" in page_doc["page_type"]
    if in_section(page_doc["page_num"], "index_page", inventory_info):
        return "index_page" in page_doc["page_type"]
    if in_section(page_doc["page_num"], "resolution_page", inventory_info):
        return "resolution_page" in page_doc["page_type"]
    # outside these ranges, page_type must be either empty, title_page or unknown_page_type
    for page_type in ["empty_page", "title_page", "unknown_page_type"]:
        if page_type in page_doc["page_type"]:
            return True
    return False


def get_correct_page_type(page_doc: dict, inventory_info: dict) -> str:
    if in_section(page_doc["page_num"], "respect_page", inventory_info):
        return "respect_page"
    if in_section(page_doc["page_num"], "index_page", inventory_info):
        return "index_page"
    if in_section(page_doc["page_num"], "resolution_page", inventory_info):
        return "resolution_page"
    if page_doc["page_num"] in inventory_info["title_page_nums"]:
        return "title_page"
    else:
        return "empty_page"


def correct_page_type_external_info(rep_es: RepEs, es: Elasticsearch, inventory_info: dict, inv_num: int, inv_config: dict) -> None:
    print("correcting page_type using external info for inventory", inv_num)
    pages = rep_es.retrieve_inventory_pages(es, inv_num, inv_config)
    pages.sort(key = lambda x: x["page_num"])
    print("pages retrieved for inventory", inv_num)
    for page_doc in pages:
        correct_page_type = get_correct_page_type(page_doc, inventory_info[inv_num])
        if correct_page_type in page_doc["page_type"]:
            #print("CORRECT:", page_doc["page_num"], page_doc["page_type"])
            continue
        print(inv_num, page_doc["page_num"], swap_page_type(page_doc, correct_page_type), page_doc["page_type"])
        page_doc["page_type"] = swap_page_type(page_doc, correct_page_type)
        if correct_page_type == "index_page":
            late_print_starts = inv_config["index_page_late_print"]["inventory_threshold"]
            period_type = "index_page_early_print" if inv_num < late_print_starts else "index_page_late_print"
            page_doc["page_type"] += [period_type]
        rep_es.index_page(es, page_doc, inv_config)


def correct_single_page_type(rep_es: RepEs, es: Elasticsearch, page_num: int, section: dict, inventory_config: dict) -> bool:
    section_types = ["index_page", "resolution_page", "respect_page", "unknown_page_type"]
    correct_page_type = section["page_type"]
    page_doc = rep_es.retrieve_page_by_page_number(es, page_num, inventory_config)
    if not page_doc:
        print("no document for page number", page_num)
        return False
    if "empty_page" in page_doc["page_type"] and section["end"] - page_num < 5:
        # empty pages at the end of section should keep page_type "empty_page"
        return False
    if "page_type" not in page_doc:
        print("No page_type in page_doc:", page_doc["page_num"], page_doc["page_id"], page_doc["scan_num"])
        print(page_doc["num_columns"])
        page_doc["page_type"] = [correct_page_type]
        if correct_page_type == "index_page":
            if inventory_config["inventory_num"] <= inventory_config["index_page_early_print"]["inventory_threshold"]:
                page_doc["page_type"] += ["index_page_early_print"]
            else:
                page_doc["page_type"] += ["index_page_late_print"]
        return True
    if correct_page_type != "index_page" and "index_page" in page_doc["page_type"]:
        page_doc["page_type"] = [page_type for page_type in page_doc["page_type"] if
                                 "index_page" not in page_doc["page_type"]]
    if correct_page_type not in page_doc["page_type"]:
        # incorrect_type = [page_type for page_type in page_doc["page_type"] if page_type in section_types]
        page_doc["page_type"] = [page_type for page_type in page_doc["page_type"] if page_type not in section_types]
        page_doc["page_type"] += [correct_page_type]
        # print(page_doc["page_num"], page_doc["page_type"])
        rep_es.index_page(es, page_doc, inventory_config)
        # print(page_doc["page_num"], "correcting", incorrect_type, "to", page_type)
        if correct_page_type == "index_page":
            if inventory_config["inventory_num"] <= inventory_config["index_page_early_print"]["inventory_threshold"]:
                page_doc["page_type"] += ["index_page_early_print"]
            else:
                page_doc["page_type"] += ["index_page_late_print"]
        return True
    return False


def correct_page_types(es: Elasticsearch, inventory_config: dict):
    print("Gathering section information for inventory", inventory_config["inventory_num"])
    inventory_data = inv_analyser.get_inventory_summary(es, inventory_config)
    for section in inventory_data["sections"]:
        corrected = 0
        for page_num in range(section["start"], section["end"]+1):
            if correct_single_page_type(es, page_num, section, inventory_config):
                corrected += 1
            #else:
            #    print(page_doc["page_num"], "correct")
        print("Inventory {} section {} ({}-{})\tcorrected types of {} pages".format(inventory_config["inventory_num"],
                                                                                    section["page_type"],
                                                                                    section["start"],
                                                                                    section["end"], corrected))
    print("\nDone!")


def correct_page_types_old(rep_es: RepEs, es: Elasticsearch, config: dict):
    ordered_page_ids = get_ordered_page_ids(es, config)
    ordered_parts = ["index_page", "resolution_page"]  # "non_text_page",
    prev_part = None
    prev_is_title_page = None
    current_part = None
    for page_id in ordered_page_ids:
        page_doc = rep_es.retrieve_page_by_id(es, page_id, config)
        if not page_doc:
            continue  # skip unindexed pages
        if page_doc["is_title_page"] and not prev_is_title_page:
            current_part = ordered_parts[0]
            print("Switching to part", current_part)
            if len(ordered_parts) > 1:
                ordered_parts = ordered_parts[1:]
        if current_part != page_doc["page_type"]:
            # update page type and re-index
            if page_doc["page_type"] == "bad_page":
                page_doc["is_parseable"] = False
            else:
                page_doc["is_parseable"] = True
            print("correcting:", page_id, "from type", page_doc["page_type"], "to type", current_part)
            page_doc["page_type"] = current_part
            doc = rep_es.create_es_page_doc(page_doc)
            es.index(index=config["page_index"], doc_type=config["page_doc_type"], id=page_id, body=doc)
        prev_part = current_part
        prev_is_title_page = page_doc["is_title_page"]
    print("\nDone!")


def get_page_pairs(rep_es: RepEs, ordered_page_ids: list) -> iter:
    for curr_page_index, curr_page_id in enumerate(ordered_page_ids):
        if curr_page_index == 0:  # skip
            continue
        curr_page_doc = rep_es.retrieve_page_by_id(curr_page_id)
        prev_page_id = ordered_page_ids[curr_page_index - 2]
        prev_page_doc = rep_es.retrieve_page_by_id(prev_page_id)
        yield curr_page_doc, prev_page_doc


def get_ordered_page_ids(es: Elasticsearch, config: dict) -> list:
    query = {"query": {"term": {"inventory_year": config["year"]}}, "_source": ["page_num", "page_id"],
             "size": 10000}
    # query = {"query": {"term": {"inventory_year": config["year"]}}}
    response = es.search(index=config["page_index"], doc_type=config["page_doc_type"], body=query)
    if response["hits"]["total"] == 0:
        return []
    pages_info = [hit["_source"] for hit in response["hits"]["hits"]]
    return [page_info["page_id"] for page_info in sorted(pages_info, key=lambda x: x["page_num"])]


def detect_duplicate_scans(rep_es: RepEs, es: Elasticsearch, config: dict):
    ordered_page_ids = get_ordered_page_ids(es, config)
    for curr_page_doc, prev_page_doc in get_page_pairs(es, ordered_page_ids, config):
        curr_page_doc["is_duplicate"] = False
        if is_duplicate(curr_page_doc, prev_page_doc, similarity_threshold=0.8):
            curr_page_doc["is_duplicate"] = True
            curr_page_doc["is_duplicate_of"] = prev_page_doc["page_id"]
            print("Page {} is duplicate of page {}".format(curr_page_doc["page_id"], prev_page_doc["page_id"]))
        doc = rep_es.create_es_page_doc(curr_page_doc)
        es.index(index=config["page_index"], doc_type=config["page_doc_type"],
                 id=curr_page_doc["page_id"], body=doc)
    print("\nDone with year {}, inventory {}!".format(config["year"], config["inventory_num"]))


########################################################################
#
# **Problem 3**: Page numbers of numbered pages are reset per part, starting from page 1,
# but the title page separating the first and second halves of the year should not reset
# the page numbering.
#
# **Solution**: Iterate over the pages, using a flag to keep track of whether we're in the
# indices part or a resolution part. If the title page is within the resolution part, update
# the page numbers by incrementing from the previous page.
#
########################################################################

def correct_page_numbers(rep_es: RepEs, es: Elasticsearch, config: dict):
    ordered_page_ids = get_ordered_page_ids(es, config)
    prev_numbered_page_number = 0
    for page_id in ordered_page_ids:
        page_doc = rep_es.retrieve_page_by_id(page_id)
        year = page_doc["inventory_year"]
        if not page_doc:  # skip unindexed pages
            continue
        # if "type_page_num_checked" in page_doc and page_doc["type_page_num_checked"]:
        #    prev_numbered_page_number += 1
        #    continue
        if "resolution_page" not in page_doc["page_type"]:  # skip non-resolution pages
            continue
        if "is_duplicate" not in page_doc:
            print("No is_duplicate field for page", page_doc["page_id"], ", inventory", page_doc["inventory_num"])
            print(page_doc.metadata['page_type'])
        if page_doc.metadata["is_duplicate"]:
            duplicated_page_doc = rep_es.retrieve_page_by_id(page_doc["is_duplicate_of"])
            print("CORRECTING FOR DUPLICATE SCAN:", page_doc["page_id"], page_doc["type_page_num"],
                  duplicated_page_doc["type_page_num"])
            page_doc["type_page_num"] = duplicated_page_doc["type_page_num"]
            # prev_numbered_page_number -= 2
        elif "resolution_page" in page_doc["page_type"] and page_doc["type_page_num"] == prev_numbered_page_number + 1:
            # print("CORRECT:", page_id, page_doc["page_type"], page_doc["type_page_num"], prev_numbered_page_number + 1)
            pass
        else:
            print("CORRECTING PAGE NUMBER OF PAGE {} FROM {} TO {}:".format(page_id, page_doc["type_page_num"],
                                                                            prev_numbered_page_number + 1))
            page_doc["type_page_num"] = prev_numbered_page_number + 1
        page_doc["type_page_num_checked"] = True
        doc = rep_es.create_es_page_doc(page_doc)
        es.index(index=config["page_index"], doc_type=config["page_doc_type"], id=page_id, doc=doc)
        prev_numbered_page_number = page_doc["type_page_num"]
    print("\nDone!")
