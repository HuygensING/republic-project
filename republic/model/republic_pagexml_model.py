from typing import List, Dict
import glob
import os
import xmltodict


def read_pagexml_file(pagexml_file: str) -> dict:
    with open(pagexml_file, 'rt') as fh:
        data = xmltodict.parse(fh.read())
        return data


def get_files(pagexml_dir: str) -> List[str]:
    return glob.glob(os.path.join(pagexml_dir, "*.xml"))


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


def check_page_assertions(page_json: dict) -> None:
    """These assertions are to check if the PageXML format changes based on additional output of OCR/HTR analysis."""
    assert(page_json['PcGts']['schemaLocation'] is None)
    assert(page_json['PcGts']['Metadata'] is None)
    if 'pcGtsId' in page_json['PcGts']:
        assert(page_json['PcGts']['pcGtsId'] is None)
    assert(page_json['PcGts']['Page']['@imageWidth'] is '0')
    assert(page_json['PcGts']['Page']['@imageHeight'] is '0')
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


def parse_textline_metadata(textline: dict):
    line = {'coords': parse_coords(textline['Coords']), 'xheight': int(textline['@xheight'])}
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


def parse_derived_coords(item_list: list) -> Dict[str, int]:
    left = item_list[0]['coords']['left']
    right = item_list[0]['coords']['right']
    top = item_list[0]['coords']['top']
    bottom = item_list[0]['coords']['bottom']
    for item in item_list:
        if item['coords']['left'] < left:
            left = item['coords']['left']
        if item['coords']['right'] > right:
            right = item['coords']['right']
        if item['coords']['top'] < top:
            top = item['coords']['top']
        if item['coords']['bottom'] > bottom:
            bottom = item['coords']['bottom']
    return {
        'left': left,
        'right': right,
        'top': top,
        'bottom': bottom,
        'height': bottom - top,
        'width': right - left
    }


def parse_textline(textline: dict):
    check_textline_assertions(textline)
    line = parse_textline_metadata(textline)
    line['text'] = textline['TextEquiv']['Unicode']
    return line


def parse_textline_list(textline_list: list):
    return [parse_textline(textline) for textline in textline_list]


def parse_textregion(textregion: dict):
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


def parse_textregion_list(textregion_list: list):
    return [parse_textregion(textregion) for textregion in textregion_list]


def parse_pagexml(page_json: dict):
    check_page_assertions(page_json)
    page_json = page_json['PcGts']['Page']
    page_doc = {}
    if 'TextRegion' in page_json:
        if isinstance(page_json['TextRegion'], list):
            page_doc['textregions'] = parse_textregion_list(page_json['TextRegion'])
        else:
            page_doc['textregions'] = [parse_textregion(page_json['TextRegion'])]
    split_page_regions(page_doc)
    return page_doc


def split_page_regions(page_doc: dict):
    for textregion in page_doc['textregions']:
        if 'lines' in textregion:
            for line in textregion['lines']:
                if line['right'] < 2500:
                    line['page_side'] = "even"
                elif line['right'] < 4800 and line['left'] > 2400:
                    line['page_side'] = "odd"
                else:
                    line['page_side'] = "extra"
        if 'textregions' in textregion:
            for subregion in textregion['textregions']:
                if subregion['right'] < 2500:
                    subregion['page_side'] = "even"
                else:
                    subregion['page_side'] = "odd"


def parse_pagexml_file(pagexml_file: str):
    page_json = read_pagexml_file(pagexml_file)
    try:
        page_doc = parse_pagexml(page_json)
        return page_doc
    except (AssertionError, KeyError, TypeError):
        print(f"Parsing file {pagexml_file}")
        raise
