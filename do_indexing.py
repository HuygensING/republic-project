import os

import republic.elastic.republic_elasticsearch as rep_es
import republic.elastic.republic_indexing as rep_indexing
import republic.download.republic_data_downloader as downloader
from republic.config.republic_config import base_config, set_config_inventory_num
from republic.model.inventory_mapping import get_inventories_by_year
import republic.analyser.republic_inventory_analyser as inv_analyser
import republic.elastic.republic_page_checks as page_checker
# import republic.parser.republic_file_parser as file_parser
from republic.fuzzy.fuzzy_context_searcher import FuzzyContextSearcher
from republic.model.republic_phrase_model import resolution_phrases, spelling_variants


host_type = os.environ.get('REPUBLIC_HOST_TYPE')
print('host type form environment:', host_type)
if not host_type:
    message = """REPUBLIC_HOST_TYPE is not set, assuming "external".
                To use internal, set environment variable REPUBLIC_HOST_TYPE='internal'."""
    print()
    host_type = "external"
print('host_type:', host_type)

es_anno = rep_es.initialize_es(host_type=host_type)
es_tr = rep_es.initialize_es_text_repo()

data_type = "hocr"
base_dir = "/data/republic/"

years = [
    #1743,
    #1744,
    #1745,
    #1746,
    #1747,
    #1753,
    1763,
    1773,
    1783,
    1793
]


def zip_exists(inv_num, ocr_type, inv_config):
    out_file = downloader.get_output_filename(inv_num, ocr_type, inv_config)
    if os.path.isfile(out_file):
        return True
    else:
        return False


def has_sections(inv_num, inv_config):
    inv_metadata = rep_es.retrieve_inventory_metadata(es_anno, inv_num, inv_config)
    return "sections" in inv_metadata


def add_resolution_page_numbers(es, inv_num, metadata, inv_config):
    resolution_page_offset = 0
    for offset in metadata["type_page_num_offsets"]:
        if offset["page_type"] == "resolution_page":
            resolution_page_offset = offset["page_num_offset"]
    print(inv_num, "resolution_page_offset:", resolution_page_offset)
    page_docs = rep_es.retrieve_resolution_pages(es, inv_num, inv_config)
    for page_doc in sorted(page_docs, key = lambda x: x["metadata"]["page_num"]):
        type_page_num = page_doc["metadata"]["page_num"] - resolution_page_offset + 1
        if type_page_num <= 0:
            page_doc["metadata"]["page_type"].remove("resolution_page")
            #print(inv_num, page_doc["page_num"], page_doc["page_type"])
        else:
            page_doc["metadata"]["type_page_num"] = type_page_num
        #print(inv_num, page_doc["page_num"], page_doc["type_page_num"])
        rep_indexing.index_page(es, page_doc, inv_config)


def do_downloading(inv_num, inv_config, year):
    ocr_type = inv_config['ocr_type']
    print(f"Downloading {ocr_type} zip file for inventory {inv_num} (year {year})...")
    downloader.download_inventory(es_anno, inv_num, ocr_type, inv_config)


def do_scan_page_indexing_hocr(inv_num, inv_config, year):
    ocr_type = inv_config["ocr_type"]
    print(f"Indexing {ocr_type} scans and pages for inventory {inv_num} (year {year})...")
    if zip_exists(inv_num, ocr_type, inv_config):
        rep_es.index_inventory_from_zip(es_anno, inv_num, inv_config)


def do_scan_indexing_pagexml(inv_num, inv_config, year):
    ocr_type = inv_config["ocr_type"]
    print(f"Indexing {ocr_type} scans for inventory {inv_num} (year {year})...")
    rep_es.index_inventory_scans_from_text_repo(es_anno, es_tr, inv_num, inv_config)


def do_page_indexing_pagexml(inv_num, inv_config, year):
    ocr_type = inv_config["ocr_type"]
    print(f"Indexing {ocr_type} pages for inventory {inv_num} (year {year})...")
    rep_es.index_inventory_pages_from_scans(es_anno, inv_num)


def do_inventory_metadata_indexing_hocr(inv_num, inv_config, year):
    print(f"Indexing hocr inventory metadata for inventory {inv_num} (year {year})...")
    inv_summary = inv_analyser.get_inventory_summary(es_anno, inv_config)
    metadata = inv_analyser.make_inventory_metadata_doc(es_anno, inv_num,
                                        inv_summary, inv_config)
    rep_es.index_inventory_metadata(es_anno, metadata, inv_config)


def do_page_type_correction_hocr(inv_num, inv_config, year):
    metadata = inv_analyser.get_inventory_metadata(es_anno, inv_num, inv_config)
    print(f"Updating page types for inventory {inv_num} (year {year})...")
    page_checker.correct_page_types(es_anno, inv_config)
    add_resolution_page_numbers(es_anno, inv_num, metadata, inv_config)


def do_page_type_indexing_pagexml(inv_num, inv_config, year):
    metadata = inv_analyser.get_inventory_metadata(es_anno, inv_num, inv_config)
    print(f"Updating page types for inventory {inv_num} (year {year})...")
    rep_indexing.add_pagexml_page_types(es_anno, inv_config)
    add_resolution_page_numbers(es_anno, inv_num, metadata, inv_config)


def do_typed_page_number_indexing_hocr(inv_num, inv_config, year):
    print(f"Adding hocr typed page numbers for inventory {inv_num} (year {year})...")
    metadata = inv_analyser.get_inventory_metadata(es_anno, inv_num, inv_config)
    add_resolution_page_numbers(es_anno, inv_num, metadata, inv_config)


def do_paragraph_indexing(inv_num, inv_config, year):
    print(f"Indexing hocr page paragraphs for inventory {inv_num} (year {year})...")
    config = {
        "char_match_threshold": 0.8,
        "ngram_threshold": 0.6,
        "levenshtein_threshold": 0.8,
        "ignorecase": False,
        "ngram_size": 2,
        "skip_size": 2,
    }
    keyword_searcher = FuzzyContextSearcher(config)
    keyword_searcher.index_keywords(resolution_phrases)
    keyword_searcher.index_spelling_variants(spelling_variants)
    rep_es.index_paragraphs(es_anno, keyword_searcher, inv_num, inv_config)


def do_session_lines_indexing(inv_num, inv_config, year):
    print(f"Indexing PageXML sessions for inventory {inv_num} (year {year})...")
    rep_indexing.index_inventory_sessions_with_lines(es_anno, inv_num, inv_config)


def do_session_text_indexing(inv_num, inv_config, year):
    print(f"Indexing PageXML sessions for inventory {inv_num} (year {year})...")
    rep_indexing.index_inventory_sessions_with_text(es_anno, inv_num, inv_config)


def do_resolution_indexing(inv_num, inv_config, year):
    print(f"Indexing PageXML resolutions for inventory {inv_num} (year {year})...")
    rep_indexing.index_inventory_resolutions(es_anno, inv_config)


def do_resolution_phrase_match_indexing(inv_num, inv_config, year):
    print(f"Indexing PageXML resolution phrase matches for inventory {inv_num} (year {year})...")
    rep_indexing.index_resolution_phrase_matches(es_anno, inv_config)


def do_resolution_metadata_indexing(inv_num, inv_config, year):
    print(f"Indexing PageXML resolution phrase matches for inventory {inv_num} (year {year})...")
    rep_indexing.index_inventory_resolution_metadata(es_anno, inv_config)


def process_inventory_hocr(inv_num, inv_config):
    year = inv_config["year"]
    #do_downloading(inv_num, inv_config, year)
    #do_scan_indexing_hocr(inv_num, inv_config, year)
    #do_page_indexing_hocr(inv_num, inv_config, year)
    do_scan_page_indexing_hocr(inv_num, inv_config, year)
    #do_inventory_metadata_indexing_hocr(inv_num, inv_config, year)
    #do_page_type_correction_hocr(inv_num, inv_config, year)
    #do_typed_page_number_indexing_hocr(inv_num, inv_config, year)
    #do_paragraph_indexing(inv_num, inv_config, year)


def process_inventory_pagexml(inv_num, inv_config, indexing_step):
    year = inv_config["year"]
    if indexing_step == "download":
        do_downloading(inv_num, inv_config, year)
    if indexing_step == "scans_pages":
        do_scan_indexing_pagexml(inv_num, inv_config, year)
        do_page_indexing_pagexml(inv_num, inv_config, year)
    if indexing_step == "scans":
        do_scan_indexing_pagexml(inv_num, inv_config, year)
    if indexing_step == "pages":
        do_page_indexing_pagexml(inv_num, inv_config, year)
    #if indexing_step == "metadata":
    #    do_inventory_metadata_indexing_pagexml(inv_num, inv_config, year)
    if indexing_step == "page_types":
        do_page_type_indexing_pagexml(inv_num, inv_config, year)
    #if indexing_step == "page_numbers":
    #    do_typed_page_number_indexing_pagexml(inv_num, inv_config, year)
    if indexing_step == "session-lines":
        do_session_lines_indexing(inv_num, inv_config, year)
    if indexing_step == "session_text":
        do_session_text_indexing(inv_num, inv_config, year)
    if indexing_step == "resolutions":
        do_resolution_indexing(inv_num, inv_config, year)
    if indexing_step == "phrase_matches":
        do_resolution_phrase_match_indexing(inv_num, inv_config, year)
    if indexing_step == "resolution_metadata":
        do_resolution_metadata_indexing(inv_num, inv_config, year)


def process_inventories(inv_years, ocr_type, indexing_step):
    for inv_map in get_inventories_by_year(inv_years):
        inv_num = inv_map["inventory_num"]
        inv_config = set_config_inventory_num(inv_num, ocr_type, base_config, base_dir=base_dir)
        if ocr_type == "hocr":
            process_inventory_hocr(inv_num, inv_config, indexing_step)
        elif ocr_type == "pagexml":
            process_inventory_pagexml(inv_num, inv_config, indexing_step)


if __name__ == "__main__":
    import getopt
    import sys

    # Get the arguments from the command-line except the filename
    argv = sys.argv[1:]
    try:
        # Define the getopt parameters
        opts, args = getopt.getopt(argv, 's:e:i:', ['foperand', 'soperand'])
        start, end, indexing_step = None, None, None
        for opt, arg in opts:
            if opt == '-s':
                start = int(arg)
            if opt == '-e':
                end = int(arg)
            if opt == '-i':
                indexing_step = arg
            #print(f'opt: {opt} arg: {arg}')
        if not start or not end or not indexing_step:
            print ('usage: add.py -s <start_year> -e <end_year> -i <indexing_step>')
            sys.exit(2)
        years = [year for year in range(start, end+1)]

    except getopt.GetoptError:
        # Print something useful
        print ('usage: add.py -s <start_year> -e <end_year> -i <indexing_step>')
        sys.exit(2)
    #years = [year for year in range(1705, 1797)]
    #years = [year for year in range(1705, 1725)]
    #years = [1725, 1740]
    # Jesse respecten years
    #years = [1752, 1755, 1756, 1770, 1771, 1772, 1785]
    print(f'indexing {indexing_step} for years', years)
    ocr_type = "pagexml"
    process_inventories(years, ocr_type, indexing_step)


