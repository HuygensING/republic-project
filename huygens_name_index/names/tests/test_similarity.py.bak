#! /usr/bin/python    
#encoding=utf-8
import unittest
from unittest import TestCase 
from names.name import Name
from names.similarity import Similarity
from lxml import etree

def ratio(x,y, explain=0):
    #ratio takes two Name instances anc compares them
    return Similarity.ratio(x,y, explain)
    
class NaamSimilarityTestCase(TestCase):
    
    def print_ratio_debug(self, n1, n2):
        s = '\n%s: %s <-> %s\n%s\n' % ( ratio(n1,n2), n1.get_volledige_naam(), n2.get_volledige_naam(), ratio(n1, n2, 1)) 
        return s
    
    def assert_similarity_order(self,ls):
        """assert that the names in de list are similar in the order given to the first name in the list"""
        n0 = ls[0]
        family_name = ls[1]

        for n in ls[2:]:
            debug_s = ''
            debug_s += self.print_ratio_debug(n0, family_name)
            debug_s += self.print_ratio_debug(n0, n)
#            debug_s = debug_s.encode('latin1')
            assert ratio(n0, family_name) >= ratio(n0, n), debug_s

            family_name = n
  
    def assert_more_similar(self, ls):
        """assert that the Name pairs in this list are ordered by similairy """
        def debug_s(ls):
            s = "Expected the score to be ordered descendingly:\n"
            for n1, n2 in ls:
                s += self.print_ratio_debug(n1, n2)
            return s
        last_score = 1.1
        for n1, n2 in ls:
            r = ratio(n1, n2) 
        
            
            assert r < last_score, debug_s(ls)
            last_score = r
            
    def test_similarity(self):
        n1 = Name('Jelle Gerbrandy')
        n2 = Name('Jelle Gerbkandy')
        n3 = Name('Pietje Puk')
        n4 = Name('Jelle Gerbrandy', geslachtsnaam='Gerbrandy')
        n5 = Name('Piet Gerbrandy', geslachtsnaam='Gerbrandy')
        n6 = Name('Piet Gerbrandy', geslachtsnaam='Piet')

        self.assert_similarity_order([
            Name('Jelle Gerbrandy'),
            Name('J. Gerbrandy'),
            Name('P. Gerbrandy')
            ])


        self.assert_similarity_order([n1, n2, n3])
        self.assert_similarity_order([n5, n4, n6])
        

        #ik zoui graa gwillen dat Jelle Gerbrandy meer op J. Gerbrandy lijkt dan op Pelle Gerbrandy
        self.assert_similarity_order([
            Name('Jelle Gerbrandy'),
            Name('J. Gerbrandy'),
            Name('P. Gerbrandy')
            ])

        self.assert_similarity_order([
                Name('Jansz., Willem'), 
                Name('Jansz., Wouter'), 
                Name('Jonge, Willem de'),
            ])

        
        self.assert_similarity_order([
                Name('Hermans, A.'), 
                Name('Hermans'),
                Name('Hermansz'), 
                Name('Hermans, P.'), 
            ])

        self.assert_similarity_order([
            Name('Campen, Abraham Willem van'),
            Name('Kampen, Pieter Nicolaas van'),
            Name('Campensnieuwland, De Jonge van'),
            ])

        self.assert_similarity_order([
            Name('Kluit, Jan van'),
            Name('Kluyt, Jan'),
            Name('Kluyt, J.'),
            Name('Kluyt, Petrus'),
#            Name('Cluyt, Pieter'),
            Name(u'Cluts, Daniël'),
            ])

        self.assert_similarity_order([
            Name('vaal'),
            Name('Vaal, Jacob'),
            Name().from_string('<persName><name type="geslachtsnaam">Waal</name>, Henri van de</persName>'),
            Name('Waal, Henri van de'),

            ])

        self.assert_similarity_order([
            Name('gerbrandy'),
            Name('Gerbrandij, Pieter'),
            Name('Gerbrandus'),

            ])

        self.assert_similarity_order([
           Name('Haack, Simon'),
           Name('Haak, Simon'),
           Name('Haack, Petrus'),                           
           ])
        
        
        #oldenbarnevelt lijkt (ongeveer) evenveel op het ena als op de andere
        self.assert_similarity_order([
           Name('oldenbarnevelt'),
           Name('Oldenbarnevelt, Willem van '),
           Name('Oldenbarnevelt, dr. Johan van'),                           
           ])
       
       
        self.assert_similarity_order([
          Name('Hendrik IV'),
          Name('Hendrick IV'),
          Name('Hendrik V'),
          Name('Filips IV'),
          Name('Hendrik'),
                                      
          ])
        self.assert_similarity_order([
          Name(voornaam='(Hans) Christian'),
          Name(voornaam='Christian'),
          Name('Johan Christiaan'),                          
          ])
        
        self.assert_similarity_order([
            Name('Aerssen-Walta, Lucia van'),
            Name('Walta, Lucia van'),
            Name('Aerssens, Lucia van'),
            Name('Harselaar, Willem van'),
            Name('St. Luc, Jacques de'),
        ])
        
    
        self.assert_similarity_order([
            Name('Constant Rebecque De Villars, Jules Thierry Nicolas baron de'),
            Name('Constant Rebecque, J.V. baron de'),
            Name('Constant Rebecque, Mr. Charles Theodore Jean baron de'),
#            Name('Constantijn'),
#            Name('Rebecque, J.F. de Constant'),
            
        ])    
        self.assert_similarity_order([
            Name('Willem III'), 
            Name('koning Willem III'), 
            Name('Willem'),
        ])                               
        
        self.assert_similarity_order([
            Name("Pierre de l'Oyseleur dit de Villiers, (hof)predikant"), 
            Name("L'Oyseleur Dit de Villiers, Pierre "),
            Name('Villiers, Anne'),
            Name('Philips'),
#            Name('Willem III'), 
        ])
        
        
        #deze heeft een larger score dan heel veel and
        benchmark =  (Name('Craen, Anna'), Name('Craen, Andrea'))
        benchmark_top =  (Name('Jacob Dirks'), Name('Dirks, Mr. Jacob'))
        self.assert_more_similar([
            (Name('Engelmann, Theodoor Wilhelm'), Name('Th.W. Engelmann')),
            benchmark
          ])
        self.assert_more_similar([
            (Name('Borret, Theodorus Josephus Hubertus'), Name('Borret, Prof. Dr. Theodoor Joseph Hubert')),
            benchmark
          ])
              
        self.assert_more_similar([
            (Name('Buyts, Helena'), Name('Buydts, Helena   ')),
            benchmark
          ])

        self.assert_more_similar([
            (Name('Craen, Jelle Douwe'), Name('Craen, Jelle')),
            benchmark
          ])
        self.assert_more_similar([
            (Name('Herman Johan Royaards'), Name('Royaards, Hermannus')),
            benchmark
          ])    
        self.assert_more_similar([
            (Name('Carl Peter Thunberg'), Name('Thunberg, Dr. Karl Peter')),
            benchmark
          ])    
        self.assert_more_similar([
            (Name('Johanness Henricus Scholten'), Name('Scholten, J.H.')),
#            (Name('Johanness Henricus Scholten'), Name('Scholten, J.')),
            benchmark
          ])    
        
        self.assert_more_similar([
            (Name('Johannes Steenmeijer'), Name('Steenmeyer, Johannes')),
            benchmark
          ])            
        self.assert_more_similar([
            (Name(u'Johannes Stéénmeijer'), Name('Steenmeyer, Johannes')),
            benchmark
          ])            
        self.assert_more_similar([
            (Name(u'Maria, gravin van Nassau (1)'), Name('Maria, gravin van Nassau (2)')),
            benchmark
          ])             
      
        self.assert_more_similar([
            (Name(geslachtsnaam='des Amorie van der Hoeven', voornaam='Abraham'), Name('Hoeven, Abraham des Amorie van der (1)')),
            benchmark
          ])             
        
        self.assert_more_similar([
           (Name('oldenbarnevelt'), Name('Oldenbarnevelt, dr. Johan van')),   #                        
           benchmark,
           ])
 
        self.assert_more_similar([
           (Name('oldenbarnevelt'),  Name('Oldenbarnevelt, Willem van ')),
           benchmark,
           ])
        self.assert_more_similar([
           (Name('Prof. Dr. Ing. Jhr. Johan Brootjens'),  Name('Johan Brootjens')),
           benchmark,
           ])
        self.assert_more_similar([
           (Name('Apostool, C.'),  Name('Cornelis Apostool')),
           benchmark,
           ])
        
        self.assert_more_similar([
             benchmark_top,
            (Name(u'Feith, Rhijnvis'), Name('Feith, Johan Adriaan' )), 
        ])   
        
        #sommelsdijk en zieverwijzingen (=  francois van aerssen)
        #http://magnum.inghist.nl/namenindex/naam/1031229 (bovenste lijkt niet helemaal goed)
        #"prince of wales"
        #
    def test_average_distance(self):
        d = Similarity.average_distance
        self.assertEqual(d(['x'], ['x']), 1.0)
        self.assertEqual(d(['Xxx'], ['Xxx']), 1.0)
        self.assertEqual(d(['Xxx', 'y'], ['Xxx','y']), 1.0)
        self.assertEqual(d(['y', 'Xxx'], ['Xxx','y']), 1.0)
        self.assertTrue(0 < d(['Xxx'], ['Xxx','y']) < 1.0)
        self.assertTrue(0 < d(['Xxx', 'z'], ['Xxx','y']) < 1.0)
        self.assertTrue(0 < d(['Xxx', 'z'], ['Xxx'])< 1.0)
        
        self.assertEqual(d(['Xxz', 'z'], ['Xxx','y']) , d(['Xxx', 'y'],['Xxz', 'z']) )
#        self.assertEqual(d(['Xxx',], ['Xxx','y']), 1.0)

    def test_extremes(self):
        self.assertEqual(Similarity.ratio(Name('XXX'), Name('XXX')), 1.0, Similarity.ratio(Name('XXX'), Name('XXX'), explain=1))

    def test_equal(self):
        n1 = Name('Kees van Dongen')
        n2 = Name('Dongen, Kees van')
        self.assertEqual(ratio(n1, n2), 1.0)
        n1 = Name('Mercier, Camier')
        n2 = Name('Camier Mercier')
        self.assertEqual(ratio(n1, n2), 1.0)
        
        n1 = etree.fromstring('<persName>Kees van Dongen</persName>') #@UndefinedVariable
        n1 = Name().from_xml(n1)
        n2 = etree.fromstring('<persName>Dongen, Kees van</persName>') #@UndefinedVariable
        n2 = Name().from_xml(n2)
        self.assertEqual(n1.guess_normal_form(), n2.guess_normal_form())
        self.assertEqual(ratio(n1, n2), 1.0)
        
        n3 = etree.fromstring('<persName>Kees van Dongen</persName>') #@UndefinedVariable
        n3 = Name().from_xml(n3, store_guessed_geslachtsnaam=False)    
        self.assertEqual(ratio(n1, n3), 1.0)
        self.assertEqual(ratio(n2, n3), 1.0)
        
        n1 = Name('Witte van Citters, Jacob de (jhr. mr.)')
        n2 = Name('Jacob de Witte van Citters')
#        print ratio(n1, n2, explain=True)
        self.assertEqual(ratio(n1, n2), 1.0)
        
        
def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite(NaamSimilarityTestCase),
        ))

if __name__=='__main__':
    unittest.main()
    
