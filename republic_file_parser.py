import os
from collections import defaultdict
from inventory_mapping import inventory_mapping

# filename format: NL-HaNA_1.01.02_3780_0016.jpg-0-251-98--0.40.hocr

def get_files(data_dir):
    for root_dir, sub_dirs, filenames in os.walk(data_dir):
        return sorted([get_scan_info(fname, root_dir) for fname in filenames], key=lambda x: x["scan_num_column_num"])

def read_hocr_scan(scan_file):
    column_id = "{}-{}".format(scan_file["scan_num"], scan_file["scan_column"])
    hocr_index_page = make_hocr_page(scan_file["filepath"], column_id, remove_line_numbers=False, remove_tiny_words=True, tiny_word_width=6)
    hocr_index_page.scan_info = scan_file
    hocr_index_page.scan_info["num_page_ref_lines"] = count_page_ref_lines(hocr_page)
    return hocr_index_page


def get_scan_num(fname):
    return int(fname.split(".")[2].split("_")[2])

def get_inventory_num(fname):
    return int(fname.split(".")[2].split("_")[1])

def get_inventory_period(fname):
    inventory_num = get_inventory_num(fname)
    for inventory in inventory_mapping:
        if inventory_num == inventory["inventory_num"]:
            return inventory["period"]
    else:
        return None

def get_inventory_year(fname):
    inventory_num = get_inventory_num(fname)
    for inventory in inventory_mapping:
        if inventory_num == inventory["inventory_num"]:
            return inventory["year"]
    else:
        return None

def get_column_num(fname):
    return int(fname.split(".")[3].split("-")[1])

def get_scan_page_num(fname):
    page_num = get_scan_num(fname) * 2
    if get_page_side(fname) == "odd":
        page_num += 1
    return page_num

def get_scan_slant(fname):
    parts = fname.split(".")[3].split("-")
    if len(parts) == 6:
        return float(parts[5]) * -1
    elif len(parts) == 5:
        return float(parts[4])
    else:
        raise TypeError("Unexpected structure of filename")

def get_page_side(fname):
    parts = fname.split(".")[3].split("-")
    if int(parts[2]) < 2200:
        return "even"
    else:
        return "odd"

def get_scan_info(fname, root_dir):
    return {
        "scan_num": get_scan_num(fname),
        "scan_column": get_column_num(fname),
        "scan_num_column_num": get_scan_num(fname) + 0.1 * get_column_num(fname),
        "inventory_num": get_inventory_num(fname),
        "inventory_year": get_inventory_year(fname),
        "inventory_period": get_inventory_period(fname),
        "page_id": "year-{}-scan-{}-{}".format(get_inventory_year(fname), get_scan_num(fname), get_page_side(fname)),
        "page_num": get_scan_page_num(fname),
        "page_side": get_page_side(fname),
        "slant": get_scan_slant(fname),
        "column_id": "scan-{}-{}-{}".format(get_scan_num(fname), get_page_side(fname), get_column_num(fname)),
        "filepath": os.path.join(root_dir, fname)
    }

def gather_page_columns(scan_files):
    page_info = defaultdict(list)
    for scan_file in scan_files:
        if scan_file["page_id"] not in page_info:
            page_info[scan_file["page_id"]] = {
                "scan_num": scan_file["scan_num"],
                "inventory_num": scan_file["inventory_num"],
                "inventory_year": scan_file["inventory_year"],
                "inventory_period": scan_file["inventory_period"],
                "page_id": scan_file["page_id"],
                "page_num": scan_file["page_num"],
                "page_side": scan_file["page_side"],
                "columns": []
            }
        page_info[scan_file["page_id"]]["columns"] += [scan_file]
    return page_info


