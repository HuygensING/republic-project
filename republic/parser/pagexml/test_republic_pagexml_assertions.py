from typing import Dict
from dateutil.parser import parse as date_parse
import re


##############################################################
# Assertion code: these are specific to the Republic project #
# and are used to raise clear errors when new elements are   #
# introduced into the PageXML output.                        #
##############################################################

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
    textline_children = [
        '@id', '@xheight', '@custom', 'idString', 'Coords',
        'Baseline', 'TextEquiv', 'TextStyle', 'Word'
    ]
    for child in textline:
        if child not in textline_children:
            print(textline)
            raise KeyError(f"Unknown child element in PageXML TextLine: {child}")
        if child == 'idString':
            assert(textline['idString'] is None)
        if child == 'TextStyle':
            assert(textline['TextStyle'] is None)
        if child == 'Word':
            words = textline['Word'] if isinstance(textline['Word'], list) else [textline['Word']]
            for word in words:
                check_word_assertions(word)


def check_word_assertions(word: dict) -> None:
    word_children = ['@id', '@xheight', '@custom', 'idString', 'Coords', 'Baseline', 'TextEquiv', 'TextStyle', 'Word']
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
        if child == 'TextRegion':
            trs = textregion['TextRegion'] if isinstance(textregion['TextRegion'], list) else [textregion['TextRegion']]
            for tr in trs:
                check_textregion_assertions(tr)
        if child == 'TextLine':
            lines = textregion['TextLine'] if isinstance(textregion['TextLine'], list) else [textregion['TextLine']]
            for line in lines:
                check_textline_assertions(line)


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
            elif date_parse(metadata[field]):
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


def check_reading_order_assertions(reading_order_json: dict) -> None:
    if reading_order_json is None:
        return None
    if 'OrderedGroup' in reading_order_json:
        fields = {'@id', '@caption', 'RegionRefIndexed'}
        assert reading_order_json['OrderedGroup'] is not None
        for field in reading_order_json:
            assert(field in fields)
            if field == 'RegionRefIndexed':
                assert('@index' in reading_order_json[field])
                assert('@regionRef' in reading_order_json[field])


def check_page_assertions(page_json: Dict[str, any]) -> None:
    assert(page_json['@imageWidth'].isdigit() is True)
    assert(page_json['@imageHeight'].isdigit() is True)
    if 'ReadingOrder' in page_json:
        assert(page_json['ReadingOrder'] is None or isinstance(page_json['ReadingOrder'], dict))
    if 'PrintSpace' in page_json:
        assert(page_json['PrintSpace'] is None)
    if '@imageFilename' in page_json:
        assert(isinstance(page_json['@imageFilename'], str))
    page_children = [
        'ReadingOrder', 'TextRegion', 'PrintSpace',
        '@imageWidth', '@imageHeight', '@imageFilename'
    ]
    for child in page_json:
        if child not in page_children:
            raise KeyError(f"Unknown child element in PageXML Page: {child}")
        if child == 'TextRegion':
            trs = page_json['TextRegion'] if isinstance(page_json['TextRegion'], list) else [page_json['TextRegion']]
            for text_region in trs:
                check_textregion_assertions(text_region)


def check_root_assertions(scan_json: dict) -> None:
    """These assertions are to check if the PageXML format changes based on
    additional output of OCR/HTR analysis."""
    check_pcgts_assertions(scan_json)
    if scan_json['PcGts']['Metadata']:
        check_page_metadata_assertions(scan_json['PcGts']['Metadata'])
    if 'pcGtsId' in scan_json['PcGts']:
        assert(scan_json['PcGts']['pcGtsId'] is None)
    pcgts_children = ['@xmlns', '@xmlns:xsi', '@xsi:schemaLocation', 'schemaLocation', 'Metadata', 'pcGtsId', 'Page']
    for child in scan_json['PcGts']:
        if child not in pcgts_children:
            raise KeyError(f"Unknown child element in PageXML PcGts: {child}")
    check_page_assertions(scan_json['PcGts']['Page'])


def do_test_republic_pagexml_assertions(scan_json: dict):
    check_root_assertions(scan_json)
    if 'Metadata' in scan_json['PcGts'] and scan_json['PcGts']['Metadata']:
        check_page_metadata_assertions(scan_json['PcGts']['Metadata'])
