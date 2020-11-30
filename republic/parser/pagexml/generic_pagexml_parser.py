from typing import List, Dict
from datetime import datetime
import numpy as np

from republic.model.republic_pagexml_model import parse_derived_coords


def check_textline_textequiv_assertions(text_equiv: dict) -> None:
    text_equiv_children = ['Unicode', 'PlainText']
    for child in text_equiv:
        if child not in text_equiv_children:
            raise KeyError(f"Unknown child element in PageXML TextEquiv: {child}")
        if child == 'PlainText':
            assert(text_equiv['PlainText'] is None)
        if child == 'Unicode':
            assert(isinstance(text_equiv['Unicode'], str))


def check_baseline_assertions(base_line: dict) -> None:
    base_line_children = ['@points']
    for child in base_line:
        if child not in base_line_children:
            raise KeyError(f"Unknown child element in PageXML Baseline: {child}")
        if child == '@points':
            assert(isinstance(base_line['@points'], str))


def check_textline_coords_assertions(text_line_coords: dict) -> None:
    coords_children = ['@points', 'Point']
    for child in text_line_coords:
        if child not in coords_children:
            raise KeyError(f"Unknown child element in PageXML TextLine Coords: {child}")
        if child == '@points':
            assert(isinstance(text_line_coords['@points'], str))
        if child == 'Point':
            assert(text_line_coords['Point'] is None)


def check_textline_assertions(textline: dict) -> None:
    textline_children = ['@xheight', 'idString', 'Coords', 'Baseline', 'TextEquiv', 'TextStyle']
    for child in textline:
        if child not in textline_children:
            print(textline)
            raise KeyError(f"Unknown child element in PageXML TextLine: {child}")
        if child == 'idString':
            assert(textline['idString'] is None)
        if child == 'TextStyle':
            assert(textline['TextStyle'] is None)


def check_textregion_assertions(textregion: dict) -> None:
    textregion_children = ['@orientation', 'Coords', 'TextEquiv', 'TextLine', 'TextRegion']
    assert('@orientation' in textregion)
    assert('Coords' in textregion)
    assert('TextEquiv' in textregion)
    assert (textregion['Coords'] is None)
    assert (textregion['TextEquiv'] is None)
    for child in textregion:
        if child not in textregion_children:
            raise KeyError(f"Unknown child element in PageXML TextRegion: {child}")
        if child == '@orientation':
            assert(textregion['@orientation'] == '0.0')


def check_page_metadata_assertions(metadata: dict) -> None:
    fields = ['Creator', 'Created', 'LastChange', 'TranskribusMetadata', 'Comments']
    for field in fields:
        if field in ['Creator', 'TranskribusMetadata', 'Comments']:
            assert(metadata[field] is None)
        if field in ['Created', 'LastChange']:
            assert(metadata[field].isdigit() is True)


def check_page_assertions(page_json: dict) -> None:
    """These assertions are to check if the PageXML format changes based on additional output of OCR/HTR analysis."""
    assert(page_json['PcGts']['schemaLocation'] is None)
    if page_json['PcGts']['Metadata']:
        check_page_metadata_assertions(page_json['PcGts']['Metadata'])
    if 'pcGtsId' in page_json['PcGts']:
        assert(page_json['PcGts']['pcGtsId'] is None)
    assert(page_json['PcGts']['Page']['@imageWidth'].isdigit() is True)
    assert(page_json['PcGts']['Page']['@imageHeight'].isdigit() is True)
    assert(page_json['PcGts']['Page']['ReadingOrder'] is None)
    assert(page_json['PcGts']['Page']['PrintSpace'] is None)
    pcgts_children = ['schemaLocation', 'Metadata', 'pcGtsId', 'Page']
    for child in page_json['PcGts']:
        if child not in pcgts_children:
            raise KeyError(f"Unknown child element in PageXML PcGts: {child}")
    page_children = ['ReadingOrder', 'TextRegion', 'PrintSpace', '@imageWidth', '@imageHeight']
    for child in page_json['PcGts']['Page']:
        if child not in page_children:
            raise KeyError(f"Unknown child element in PageXML Page: {child}")


def parse_textline_metadata(textline: dict) -> dict:
    line = {"coords": parse_coords(textline["Coords"]), "xheight": int(textline["@xheight"])}
    points = [point.split(",") for point in textline["Baseline"]["@points"].split(" ")]
    baselines = [int(y) for x, y in points]
    line["baseline"] = {
        "start_x": int(points[0][0]),
        "start_y": int(points[0][1]),
        "end_x": int(points[-1][0]),
        "end_y": int(points[-1][1]),
        "min": np.min(baselines),
        "max": np.max(baselines),
        "mean": np.mean(baselines),
        "median": np.median(baselines),
    }
    return line


def parse_coords(coords: dict) -> Dict[str, int]:
    check_textline_coords_assertions(coords)
    parts = coords['@points'].split(" ")
    left, top = [int(coord) for coord in parts[0].split(",")]
    right, bottom = [int(coord) for coord in parts[2].split(",")]
    test_right, test_top = [int(coord) for coord in parts[1].split(",")]
    test_left, test_bottom = [int(coord) for coord in parts[3].split(",")]
    assert(left == test_left)
    assert(right == test_right)
    assert(top == test_top)
    assert(bottom == test_bottom)
    return {
        'left': left,
        'right': right,
        'top': top,
        'bottom': bottom,
        'height': bottom - top,
        'width': right - left
    }


def parse_textline(textline: dict) -> dict:
    check_textline_assertions(textline)
    line = parse_textline_metadata(textline)
    line['text'] = textline['TextEquiv']['Unicode']
    return line


def parse_textline_list(textline_list: list) -> List[dict]:
    return [parse_textline(textline) for textline in textline_list]


def parse_textregion(textregion: dict) -> dict:
    check_textregion_assertions(textregion)
    parsed_region = {
        'orientation': float(textregion['@orientation'])
    }
    for child in textregion:
        if child == 'TextLine':
            if isinstance(textregion['TextLine'], list):
                parsed_region['lines'] = parse_textline_list(textregion['TextLine'])
            else:
                parsed_region['lines'] = [parse_textline(textregion['TextLine'])]
            parsed_region['coords'] = parse_derived_coords(parsed_region['lines'])
        if child == 'TextRegion':
            if isinstance(textregion['TextRegion'], list):
                parsed_region['textregions'] = parse_textregion_list(textregion['TextRegion'])
            else:
                parsed_region['textregions'] = [parse_textregion(textregion['TextRegion'])]
            parsed_region['coords'] = parse_derived_coords(parsed_region['textregions'])
    return parsed_region


def parse_textregion_list(textregion_list: list) -> List[dict]:
    return [parse_textregion(textregion) for textregion in textregion_list]


def parse_page_metadata(metadata_json: dict) -> dict:
    metadata = {}
    for field in metadata_json:
        if not metadata_json[field]:
            continue
        if field in ['Created', 'LastChange']:
            metadata[field] = datetime.fromtimestamp(int(metadata_json[field]) / 1000)
        elif metadata_json[field].isdigit():
            metadata[field] = int(metadata_json[field])
        elif metadata_json[field]:
            metadata[field] = metadata_json[field]
    return metadata


def parse_page_image_size(page_json: dict) -> dict:
    coords = {
        'left': 0,
        'right': 0,
        'top': 0,
        'bottom': 0,
        'width': 0,
        'height': 0
    }
    if page_json['@imageWidth'] != '0':
        coords['width'] = int(page_json['@imageWidth'])
        coords['right'] = coords['width']
    if page_json['@imageHeight'] != '0':
        coords['height'] = int(page_json['@imageHeight'])
        coords['bottom'] = coords['height']
    return coords


def parse_pagexml(scan_json: dict) -> dict:
    check_page_assertions(scan_json)
    scan_doc = {'metadata': {}}
    if 'Metadata' in scan_json['PcGts'] and scan_json['PcGts']['Metadata']:
        scan_doc['metadata'] = parse_page_metadata(scan_json['PcGts']['Metadata'])
    scan_json = scan_json['PcGts']['Page']
    if scan_json['@imageWidth'] != '0' and scan_json['@imageHeight'] != '0':
        scan_doc['coords'] = parse_page_image_size(scan_json)
    if 'TextRegion' in scan_json:
        if isinstance(scan_json['TextRegion'], list):
            scan_doc['textregions'] = parse_textregion_list(scan_json['TextRegion'])
        else:
            scan_doc['textregions'] = [parse_textregion(scan_json['TextRegion'])]
    return scan_doc


