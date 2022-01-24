from typing import List, Union, Dict
import json

from republic.model.republic_date import RepublicDate, make_republic_date
from settings import inventory_metadata_file


def read_inventory_metadata(metadata_file: str = None) -> List[Dict[str, any]]:
    if metadata_file is None:
        metadata_file = inventory_metadata_file
    with open(metadata_file, 'rt') as fh:
        return json.load(fh)


def get_inventory_by_num(inventory_num: int) -> dict:
    inventory_metadata = read_inventory_metadata()
    for inv_map in inventory_metadata:
        if inv_map["inventory_num"] == inventory_num:
            return inv_map


def get_inventories_by_year(inventory_years: Union[int, List[int]]) -> list:
    inventory_metadata = read_inventory_metadata()
    if isinstance(inventory_years, int):
        inventory_years = [inventory_years]
    return [inv_map for inv_map in inventory_metadata if inv_map["year"] in inventory_years]


def get_inventory_by_date(date: Union[str, RepublicDate]) -> dict:
    if isinstance(date, str):
        date = make_republic_date(date)
    inventories = get_inventories_by_year(date.year)
    if len(inventories) == 1:
        return inventories[0]
    else:
        for inventory in inventories:
            inv_start = make_republic_date(inventory["period"][0])
            inv_end = make_republic_date(inventory["period"][1])
            if inv_start <= date <= inv_end:
                return inventory
    raise ValueError(f"Cannot find inventory for date {date}")
