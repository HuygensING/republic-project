#! /usr/bin/env python    
# encoding=utf8

import unittest

from names.common import *

class CommonTestCase(unittest.TestCase):
    """test methods from common.py"""
    def test_to_ascii(self):
        self.assertEqual(to_ascii(u'ïéüÀ'), 'ieuA')
        self.assertEqual(to_ascii(u'françois'), 'fransois')

    def test_from_ymd(self):
        pass
    def test_to_ymd(self):
        pass
    
    def test_words(self):
        self.assertEqual(words('Abc d? 1 d223r! (xxx) * Mercier-Camier'), ['Abc', 'd?', '1', 'd223r', 'xxx', '*','Mercier', 'Camier'])
        self.assertEqual(words('a.b.c.'), ['a', 'b', 'c'])

def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite(CommonTestCase),
        ))

if __name__=='__main__':
    unittest.main()

        
