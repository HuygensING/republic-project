#! /usr/bin/env python    
# encoding=utf8

import unittest

from names.tokens import *

class TokensTestCase(unittest.TestCase):
    """test methods from common.py"""
    def test_tokens(self):
        s = 'Abc d? 1 d223r! (xxx)  *  --- \nMercier-Camier'
        t = tokens(s)
        self.assertEqual(''.join(['%s%s' % (word, tail) for word, tail in t]), s)
        
        self.assertEqual(tokens('H.P.'),[('H.', ''), ('P.', '')])
        
def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite(TokensTestCase),
        ))

if __name__=='__main__':
    unittest.main()

        
