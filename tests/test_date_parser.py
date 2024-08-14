import unittest

import pagexml.model.physical_document_model as pdm

import republic.parser.logical.date_parser as date_parser


class TestDateParser(unittest.TestCase):

    def test_line_has_year_recognises_year(self):
        line = pdm.PageXMLTextLine(text='1781')
        self.assertEqual(True, date_parser.line_is_year(line))

    def test_line_is_year_recognises_year_with_dot(self):
        line = pdm.PageXMLTextLine(text='1781.')
        self.assertEqual(True, date_parser.line_is_year(line))

    def test_line_is_year_does_not_recognise_year_out_of_range(self):
        line = pdm.PageXMLTextLine(text='2781.')
        self.assertEqual(False, date_parser.line_is_year(line))

    def test_line_is_year_does_not_recognise_year_in_long_year(self):
        line = pdm.PageXMLTextLine(text='the year is 1781')
        self.assertEqual(False, date_parser.line_is_year(line))

    def test_line_has_month_name_recognises_month(self):
        line = pdm.PageXMLTextLine(text='28 Maart.')
        self.assertEqual(True, date_parser.line_has_day_month(line, debug=2))

