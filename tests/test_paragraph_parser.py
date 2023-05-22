from unittest import TestCase

import pagexml.model.physical_document_model as pdm

import republic.parser.logical.paragraph_parser as para_parser


class TestParagraphLines(TestCase):

    def setUp(self) -> None:
        coords1 = pdm.Coords([(100, 100), (500, 100), (500, 200), (100, 200)])
        coords2 = pdm.Coords([(100, 300), (500, 300), (500, 400), (100, 400)])
        coords3 = pdm.Coords([(100, 500), (200, 500), (200, 600), (100, 600)])
        self.line1 = pdm.PageXMLTextLine(doc_id='line1', text='Test line', coords=coords1)
        self.line2 = pdm.PageXMLTextLine(doc_id='line1', text='Another line', coords=coords2)
        self.line3 = pdm.PageXMLTextLine(doc_id='line1', text=None, coords=coords3)

    def test_paragraph_lines_can_be_empty(self):
        para_lines = para_parser.ParagraphLines()
        self.assertEqual(0, len(para_lines))
