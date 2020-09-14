from typing import Dict


# 1724 (from 22 Sep, scan 334, page 666, cause: internal numbered pages 593-596 are misplaced, after 576)
# 1785 pages out of order
# typed page nums (scan_page_nums):
# 1215/1216 (571/572) -
# 1219/1220 (573/574) -
# 1217/1218 (575/576) -
# 1221/1222 (577/578))

def fix_page_order():
    return None


def parse_derived_coords(item_list: list) -> Dict[str, int]:
    """Return the coordinates of a box around a given list of items that each have their own coordinates."""
    for item in item_list:
        if 'coords' not in item:
            raise KeyError("items in list should have a 'coords' property")
    if len(item_list) == 0:
        left, right, top, bottom = 0, 0, 0, 0
    else:
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


class PageObject(object):

    def __init__(self, item: dict):
        assert 'coords' in item
        self.coords = item['coords']
        self.left = item['coords']['left']
        self.right = item['coords']['right']
        self.top = item['coords']['top']
        self.bottom = item['coords']['bottom']
        self.width = item['coords']['width']
        self.height = item['coords']['height']


class PageLine(PageObject):

    def __init__(self, line: dict):
        PageObject.__init__(self, line)
        assert 'xheight' in line
        assert 'text' in line
        self.xheight = line['xheight']
        self.text = line['text']
