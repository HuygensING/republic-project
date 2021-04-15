from typing import List, Dict
from datetime import datetime
import re

import numpy as np

from republic.model.physical_document_model import Baseline, Coords, parse_derived_coords
from republic.model.physical_document_model import PageXMLTextLine, PageXMLTextRegion, PageXMLWord
from republic.model.physical_document_model import PageXMLDoc, PageXMLScan, PageXMLPage, PageXMLColumn


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
    coords_children = ['@points', 'Point', '@xmlns']
    for child in text_line_coords:
        if child not in coords_children:
            raise KeyError(f"Unknown child element in PageXML TextLine Coords: {child}")
        if child == '@points':
            assert(isinstance(text_line_coords['@points'], str))
        if child == 'Point':
            assert(text_line_coords['Point'] is None)


def check_textline_assertions(textline: dict) -> None:
    textline_children = ['@id', '@xheight', 'idString', 'Coords', 'Baseline', 'TextEquiv', 'TextStyle', 'Word']
    for child in textline:
        if child not in textline_children:
            print(textline)
            raise KeyError(f"Unknown child element in PageXML TextLine: {child}")
        if child == '@id':
            assert(len(textline['@id'].split('-')) == 5)
        if child == 'idString':
            assert(textline['idString'] is None)
        if child == 'TextStyle':
            assert(textline['TextStyle'] is None)


def check_word_assertions(word: dict) -> None:
    word_children = ['@id', '@xheight', 'idString', 'Coords', 'Baseline', 'TextEquiv', 'TextStyle', 'Word']
    for child in word:
        if child not in word_children:
            print(word)
            raise KeyError(f"Unknown child element in PageXML TextLine: {child}")
        if child == '@id':
            assert(len(word['@id'].split('-')) == 5)
        if child == 'idString':
            assert(word['idString'] is None)
        if child == 'TextStyle':
            assert(word['TextStyle'] is None or '@xmlns' in word['TextStyle'])


def check_textregion_assertions(textregion: dict) -> None:
    textregion_children = ['@id', '@custom', '@orientation', 'Coords', 'TextEquiv', 'TextLine', 'TextRegion']
    # assert('@orientation' in textregion)
    assert('Coords' in textregion)
    assert('TextEquiv' in textregion)
    if textregion['Coords'] is None:
        pass
    elif isinstance(textregion['Coords'], dict) and '@points' in textregion['Coords']:
        assert (re.match(r'^\d+,\d+( \d+,\d+)+$', textregion['Coords']['@points']))
    # assert (textregion['TextEquiv'] is None)
    for child in textregion:
        if child not in textregion_children:
            raise KeyError(f"Unknown child element in PageXML TextRegion: {child}")
        if child == '@orientation':
            assert(textregion['@orientation'] == '0.0')


def check_page_metadata_assertions(metadata: dict) -> None:
    fields = ['Creator', 'Created', 'LastChange', 'TranskribusMetadata', 'Comments']
    for field in fields:
        if field in ['TranskribusMetadata', 'Comments']:
            if field not in metadata:
                pass
            elif isinstance(metadata[field], dict):
                pass
            else:
                assert(metadata[field] is None)
        if field in ['Creator']:
            assert(metadata[field] is None or isinstance(metadata[field], str))
        if field in ['Created', 'LastChange']:
            if metadata[field].isdigit():
                pass
            elif datetime.strptime(metadata[field], "%Y-%m-%dT%H:%M:%S"):
                pass
            else:
                raise ValueError(f"metadata field {field} should be numeric or date string.")


def check_pcgts_assertions(page_json: Dict[str, any]) -> None:
    pagexml_ns = "http://schema.primaresearch.org/PAGE/gts/pagecontent/2013-07-15"
    if 'schemaLocation' in page_json['PcGts']:
        assert (page_json['PcGts']['schemaLocation'] is None)
    elif '@xmlns' in page_json['PcGts']:
        assert (page_json['PcGts']['@xmlns'] == pagexml_ns)
    else:
        raise KeyError('Expected schemaLocation or @xmlns attribute')


def check_page_assertions(page_json: Dict[str, any]) -> None:
    assert(page_json['PcGts']['Page']['@imageWidth'].isdigit() is True)
    assert(page_json['PcGts']['Page']['@imageHeight'].isdigit() is True)
    if 'ReadingOrder' in page_json['PcGts']['Page']:
        assert(page_json['PcGts']['Page']['ReadingOrder'] is None)
    if 'PrintSpace' in page_json['PcGts']['Page']:
        assert(page_json['PcGts']['Page']['PrintSpace'] is None)
    if '@imageFilename' in page_json['PcGts']['Page']:
        assert(isinstance(page_json['PcGts']['Page']['@imageFilename'], str))


def check_root_assertions(page_json: dict) -> None:
    """These assertions are to check if the PageXML format changes based on
    additional output of OCR/HTR analysis."""
    check_pcgts_assertions(page_json)
    if page_json['PcGts']['Metadata']:
        check_page_metadata_assertions(page_json['PcGts']['Metadata'])
    if 'pcGtsId' in page_json['PcGts']:
        assert(page_json['PcGts']['pcGtsId'] is None)
    check_page_assertions(page_json)
    pcgts_children = ['@xmlns', 'schemaLocation', 'Metadata', 'pcGtsId', 'Page']
    for child in page_json['PcGts']:
        if child not in pcgts_children:
            raise KeyError(f"Unknown child element in PageXML PcGts: {child}")
    page_children = [
        'ReadingOrder', 'TextRegion', 'PrintSpace',
        '@imageWidth', '@imageHeight', '@imageFilename'
    ]
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
        "min": int(np.min(baselines)),
        "max": int(np.max(baselines)),
        "mean": int(np.mean(baselines)),
        "median": int(np.median(baselines)),
    }
    return line


def parse_coords(coords: dict) -> Coords:
    check_textline_coords_assertions(coords)
    return Coords(points=coords['@points'])


def parse_baseline(baseline: dict) -> Baseline:
    check_textline_coords_assertions(baseline)
    return Baseline(points=baseline['@points'])


def parse_coords_old(coords: dict) -> Dict[str, int]:
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


def parse_line_words(textline: dict) -> List[PageXMLWord]:
    words: List[PageXMLWord] = []
    if "Word" not in textline:
        return words
    if isinstance(textline["Word"], dict):
        textline["Word"] = [textline["Word"]]
    for word_dict in textline["Word"]:
        check_word_assertions(word_dict)
        word = PageXMLWord(text=word_dict["TextEquiv"]["Unicode"]['#text'],
                           coords=parse_coords(word_dict["Coords"]),
                           conf=word_dict["TextEquiv"]["@conf"] if "@conf" in word_dict["TextEquiv"] else None)
        words.append(word)
    return words


def parse_textline(textline: dict) -> PageXMLTextLine:
    check_textline_assertions(textline)
    line = PageXMLTextLine(xheight=int(textline["@xheight"]) if '@xheight' in textline else None,
                           coords=parse_coords(textline["Coords"]),
                           baseline=parse_baseline(textline["Baseline"]),
                           text=textline["TextEquiv"]["Unicode"],
                           words=parse_line_words(textline))
    return line


def parse_textline_list(textline_list: list) -> List[PageXMLTextLine]:
    return [parse_textline(textline) for textline in textline_list]


def parse_custom_metadata(textelement: Dict[str, any]) -> Dict[str, any]:
    metadata = {}
    if '@custom' not in textelement:
        return metadata
    if 'structure {' in textelement['@custom']:
        match = re.search(r'\bstructure {(.*?)}', textelement['@custom'])
        if not match:
            print(textelement)
            raise ValueError('Invalid structure metadata in custom attribute.')
        structure_parts = match.group(1).strip().split(';')
        for part in structure_parts:
            if part == '':
                continue
            field, value = part.split(':')
            metadata[field.strip()] = value.strip()
    return metadata


def parse_textregion(text_region_dict: dict) -> PageXMLTextRegion:
    check_textregion_assertions(text_region_dict)
    coords_dict = text_region_dict['Coords'] if 'Coords' in text_region_dict else None
    text_region = PageXMLTextRegion(
        orientation=float(text_region_dict['@orientation']) if '@orientation' in text_region_dict else None,
        coords=parse_coords(text_region_dict['Coords']) if coords_dict else None,
        doc_id=text_region_dict['@id'] if '@id' in text_region_dict else None,
        metadata=parse_custom_metadata(text_region_dict) if '@custom' in text_region_dict else None,
    )
    if text_region.metadata and 'type' in text_region.metadata:
        text_region.add_type(text_region.metadata['type'])
    for child in text_region_dict:
        if child == 'TextLine':
            if isinstance(text_region_dict['TextLine'], list):
                text_region.lines = parse_textline_list(text_region_dict['TextLine'])
            else:
                text_region.lines = [parse_textline(text_region_dict['TextLine'])]
            if not text_region.coords:
                text_region.coords = parse_derived_coords(text_region.lines)
        if child == 'TextRegion':
            if isinstance(text_region_dict['TextRegion'], list):
                text_region.text_regions = parse_textregion_list(text_region_dict['TextRegion'])
            else:
                text_region.text_regions = [parse_textregion(text_region_dict['TextRegion'])]
            if not text_region.coords:
                text_region.coords = parse_derived_coords(text_region.text_regions)
    return text_region


def parse_textregion_list(textregion_dict_list: list) -> List[PageXMLTextRegion]:
    return [parse_textregion(textregion_dict) for textregion_dict in textregion_dict_list]


def parse_page_metadata(metadata_json: dict) -> dict:
    metadata = {}
    for field in metadata_json:
        if not metadata_json[field]:
            continue
        if field in ['Created', 'LastChange']:
            if metadata_json[field].isdigit():
                metadata[field] = datetime.fromtimestamp(int(metadata_json[field]) / 1000)
            else:
                metadata[field] = datetime.strptime(metadata_json[field], "%Y-%m-%dT%H:%M:%S")
        elif isinstance(metadata_json[field], dict):
            metadata[field] = metadata_json[field]
        elif metadata_json[field].isdigit():
            metadata[field] = int(metadata_json[field])
        elif metadata_json[field]:
            metadata[field] = metadata_json[field]
    return metadata


def parse_page_image_size(page_json: dict) -> Coords:
    w = int(page_json['@imageWidth'])
    h = int(page_json['@imageHeight'])
    points = [(0, 0), (w, 0), (w, h), (0, h)]
    return Coords(points=points)


def parse_page_image_size_old(page_json: dict) -> dict:
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


def parse_pagexml(scan_json: dict) -> PageXMLScan:
    check_root_assertions(scan_json)
    coords, text_regions = None, None
    metadata = {}
    if 'Metadata' in scan_json['PcGts'] and scan_json['PcGts']['Metadata']:
        metadata = parse_page_metadata(scan_json['PcGts']['Metadata'])
    if 'xmlns' in scan_json['PcGts']:
        metadata['namespace'] = scan_json['PcGts']['xmlns']
    scan_json = scan_json['PcGts']['Page']
    if scan_json['@imageWidth'] != '0' and scan_json['@imageHeight'] != '0':
        coords = parse_page_image_size(scan_json)
    if 'TextRegion' in scan_json:
        if isinstance(scan_json['TextRegion'], list):
            text_regions = parse_textregion_list(scan_json['TextRegion'])
        else:
            text_regions = [parse_textregion(scan_json['TextRegion'])]
    return PageXMLScan(metadata=metadata, coords=coords, text_regions=text_regions)
