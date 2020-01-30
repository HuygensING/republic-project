

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
