#! /usr/bin/env python    
# encoding=utf8

import unittest

from names.name import Name, TYPE_TERRITORIAL, TYPE_GIVENNAME, TYPE_FAMILYNAME
from lxml import etree
from names.common import *
from names.tokens import Token

class NameTestCase(unittest.TestCase):

    def tearDown(self):
        pass
 
    def test_guess_geslachtsnaam(self):
        for n, wanted_result in [
            ('Jelle Gerbrandy', 'Gerbrandy'),
#            ('Boudewijn (zie van der AA.)', 'Boudewijn'),
            ('Gerbrandy, Jelle', 'Gerbrandy'),
            ('C.H.Veenstra', 'Veenstra'),
            ('Yvette Marcus-de Groot', 'Marcus-de Groot'),
            ('S. de Groot', 'Groot'),
            ('Willy Smit-Buit' , 'Smit-Buit' ), 
            ('Hendrik', 'Hendrik'),
            ('Bec(q)-Crespin, Josina du', 'Bec(q)-Crespin'), 
            ('David Heilbron Cz.', 'Heilbron'),
            ('Arien A', 'A'),
            ('Johannes de Heer', 'Heer'),
            ('Bonnet-Broederhart. A.G.' , 'Bonnet-Broederhart.' ), 
            ('Th.W. Engelmann', 'Engelmann'),
            ('A Algra', 'Algra'),
#            ('Auger O' , 'Auger' ), 
            ]:
            guessed = Name(n).guess_geslachtsnaam()
            self.assertEqual(guessed, wanted_result)
    

    def test_guess_normal_form(self):
        self.assertEqual(Name('Arien A').guess_normal_form(), 'A, Arien'),
        for n, wanted_result in [
            (Name().from_args(geslachtsnaam='A', volledige_naam='Arien A'), 'A, Arien'),
            (Name('Brugse Meester van 1493'), 'Brugse Meester van 1493'),
            (Name('Th.W. Engelmann'), 'Engelmann, Th.W.'),
            (Name('A. Algra'), 'Algra, A.'),
#             (Name().from_string('<persName>A. Algra</persName>'), 'Algra A.')
            (Name('(G. Morton)'), 'Morton, G.'),
            (Name('Di(e)ck, Jan Gerard'), 'Dick, Jan Gerard'),
            (Name('Arien A'), 'A, Arien'),
            (Name('David Heilbron Cz.'), 'Heilbron Cz., David'),
            (Name('Johann (Johan) VII'), 'Johann VII' ), 
            (Name('Johann VII'), 'Johann VII' ), 
#            (Name('koning Willem III') , 'Willem III' ), 
            (Name(u'Crato, graaf van Nassau-Saarbrück'), u'Crato, graaf van Nassau-Saarbrück'),
            (Name(u'Wilhelmina van Pruisen - prinses van Oranje-Nassau'), 'Wilhelmina van Pruisen - prinses van Oranje-Nassau'),
            (Name(u'Henriette Adriana Louise Flora d\'Oultremont de Wégimont'), u"d'Oultremont de Wégimont, Henriette Adriana Louise Flora"),
            (Name(u'Wolrat, vorst van Nassau-Usingen dikwijls genoemd Nassau-Saarbrück'), u'Wolrat, vorst van Nassau-Usingen dikwijls genoemd Nassau-Saarbrück'),
            (Name(u'van \'s-Gravezande, Arnoldus Corneluszn. Storm'), 's-Gravezande, Arnoldus Corneluszn. Storm, van'),
            (Name('L.T. graaf van Nassau La Lecq'), 'L.T. graaf van Nassau La Lecq'),
            (Name(u'Géo d\'Aconit'), u'd\'Aconit, Géo'),
            (Name(u'J. Heemskerk Azn.'), u'Heemskerk Azn., J.'),
            ]:
            guessed = n.guess_normal_form()
            self.assertEqual(guessed, wanted_result)
        self.assertEqual(Name('A').guess_normal_form(), 'A'),

        self.assertEqual(Name('Hendrik ten Brink Hz.').guess_normal_form(), 'Brink Hz., Hendrik ten'),
    
        n1 = etree.fromstring('<persName>Kees van Dongen</persName>') #@UndefinedVariable
        n1 = Name().from_xml(n1)
        self.assertEqual(n1.guess_geslachtsnaam(), 'Dongen')
        self.assertEqual(n1.guess_normal_form(), 'Dongen, Kees van')

        n1 = etree.fromstring('<persName>Dongen, Kees van</persName>') #@UndefinedVariable
        n1 = Name().from_xml(n1)
        self.assertEqual(n1.guess_normal_form(), 'Dongen, Kees van')
        
        
    def test_html_codes(self):
        n = Name('W&eacute;l?')
        n.html2unicode()
        self.assertEqual( n.volledige_naam(), u'Wél?')
        
#    def test_strip_tussenvoegsels(self):
#        for s, result in [
#            ('van de Graaf' , 'Graaf' ),
#            ('in \'t Veld' , 'Veld' ),
#            ('van der Graaf' , 'Graaf' ),
#            ]:
#            
#            self.assertEqual(Name(s)._strip_tussenvoegels(s), result)

    def test_to_string(self):
        self.assertEqual(Name('abc').store_guessed_geslachtsnaam().to_string(),
            u'<persName><name type="geslachtsnaam">abc</name></persName>')


    def test_from_xml(self):
        s ='<persName>Jelle <name type="geslachtsnaam">Gerbrandy</name></persName>'
        n = Name().from_string(s)
#        assert 0, etree.fromstring(s).xpath('//name[@type="geslachtsnaam"]')
        self.assertEqual(n.geslachtsnaam(), 'Gerbrandy')
        self.assertEqual(n.to_string(), s)

#    def test_from_soup(self):
#        #n = Name().from_soup('Ada, gravin van Holland (1185-1223)')
#        n = Name().from_soup(u'Ada, gravin van Holland (±1185‑1223)')
#        
#        self.assertEqual(n.death, '1223', )
#        self.assertEqual(n.birth, None,n.birth)
#        self.assertEqual(n.territoriale_titel, 'gravin van Holland', n.to_string())
#        self.assertEqual(n.get_volledige_naam(), 'Ada')
#        
#        n = Name().from_soup('Xerxes, koning van Perzië 486‑465</territoriale_titel>')
#        self.assertEqual(n.get_volledige_naam(), 'Xerxes')
#        n.guess_geslachtsnaam()
#        self.assertEqual(n.get_volledige_naam(), 'Xerxes')
#        self.assertEqual(n.guess_normal_form(), 'Xerxes')
#        
#        n= Name().from_soup(u'Aäron')
#        self.assertEqual(n.guess_normal_form(), u'Aäron')
#        n= Name(u'Willem II')
#        self.assertEqual(n.guess_normal_form(), u'Willem II')
#        self.assertEqual(type(n.guess_normal_form()), type(u'Willem II'))
        
    def test_from_args(self):
        n = Name().from_args(volledige_naam='Jelle Gerbrandy', geslachtsnaam='Gerbrandy')
        s ='<persName>Jelle <name type="geslachtsnaam">Gerbrandy</name></persName>'
        self.assertEqual(n.to_string(), s)
        
        n = Name().from_args(volledige_naam='Jelle Gerbrandy', geslachtsnaam='Gerbrandy')
        s ='<persName>Jelle <name type="geslachtsnaam">Gerbrandy</name></persName>'
        self.assertEqual(n.to_string(), s)
        
        n = Name(geslachtsnaam='Gerbrandy', voornaam='Jelle', intrapositie=None)
        s = '<persName><name type="voornaam">Jelle</name> <name type="geslachtsnaam">Gerbrandy</name></persName>'
        self.assertEqual(n.to_string(), s)

        n = Name().from_args(volledige_naam='Arien A', geslachtsnaam='A')
        s ='<persName>Arien <name type="geslachtsnaam">A</name></persName>'
        self.assertEqual(n.to_string(), s)
        
    def test_diacritics(self):
        n = Name(u'Wét').store_guessed_geslachtsnaam()
        el = etree.Element('test') #@UndefinedVariable
        el.text = u'Wét'
        s = u'<persName><name type="geslachtsnaam">W\xe9t</name></persName>'
        self.assertEqual(n.to_string(), s)

    def test_serialize(self):
        s = '<a>a<b>b</b> c</a>'
        self.assertEqual(Name().serialize(etree.fromstring(s)), 'ab c') #@UndefinedVariable

        s ='<persName>Jelle <name type="geslachtsnaam">Gerbrandy</name></persName>'
        naam = Name().from_string(s)
        self.assertEqual(serialize(naam._root), 'Jelle Gerbrandy')
        self.assertEqual(naam.serialize(naam._root), 'Jelle Gerbrandy')
        self.assertEqual(naam.serialize(), 'Jelle Gerbrandy')
        self.assertEqual(naam.serialize(exclude='geslachtsnaam'), 'Jelle')


    def test_idempotence(self):
        
        #calling the guessing functions more than one time should not make any difference
        name = Name('Jelle Gerbrandy')
        name.guess_normal_form()
        xml1 = name.to_string()
        name.guess_normal_form()
        xml2 = name.to_string()
        name.guess_geslachtsnaam()
        xml3 = name.to_string()
        self.assertEqual(xml1, xml2)
        self.assertEqual(xml1, xml3)
        
    def test_normal_form(self):

        s ='<persName>Jelle <name type="geslachtsnaam">Gerbrandy</name></persName>'
        naam = Name().from_string(s)
        
        self.assertEqual(naam.geslachtsnaam(), u'Gerbrandy')
        self.assertEqual(naam.guess_normal_form(), u'Gerbrandy, Jelle')
        self.assertEqual(naam.guess_normal_form2(), u'Jelle Gerbrandy')

        naam = Name('Jelle Gerbrandy')
        self.assertEqual(naam.guess_normal_form(), u'Gerbrandy, Jelle')
        naam.guess_geslachtsnaam()
        self.assertEqual(naam.guess_normal_form2(), u'Jelle Gerbrandy')

        naam = Name('Gerbrandy, Jelle')
        self.assertEqual(naam.guess_normal_form(), u'Gerbrandy, Jelle')
        self.assertEqual(naam.guess_normal_form2(), u'Jelle Gerbrandy')

        naam = Name(voornaam='Hendrik IV')
        self.assertEqual(naam.geslachtsnaam(), '')
        self.assertEqual(naam.guess_normal_form(), u'Hendrik IV')
        self.assertEqual(naam.guess_normal_form2(), u'Hendrik IV')
        n = Name().from_string("""<persName>
<name type="voornaam">Hendrik IV</name>
</persName>""")
        n.guess_geslachtsnaam()
        assert not n.geslachtsnaam(), n.to_string()
        self.assertEqual(n.guess_normal_form(), 'Hendrik IV')
        self.assertEqual(naam.guess_normal_form2(), u'Hendrik IV')
        
        s = """<persName>
  <name type="geslachtsnaam">Xerxes</name>
</persName>"""
        n = Name().from_string(s)
        self.assertEqual(n.guess_normal_form(), 'Xerxes')
        
        s = '<persName><name type="geslachtsnaam">A</name>, Arien</persName>'
        n = Name().from_string(s)
        self.assertEqual(n.guess_normal_form(), 'A, Arien')
        self.assertEqual(n.guess_normal_form2(), 'Arien A')
        
        n = Name('A.B.J.Teulings')
        self.assertEqual(n.guess_normal_form(), 'Teulings, A.B.J.')
        self.assertEqual(n.guess_normal_form2(), 'A.B.J.Teulings')
        
        naam = Name('JOHAN (Johann) VII')   
        self.assertEqual(naam.guess_normal_form(), 'Johan VII')
        
        naam = Name().from_string('<persName><name type="geslachtsnaam">Dirk</name>, VI, Theodericus</persName>')  
        self.assertEqual(naam.guess_normal_form(), 'Dirk, VI, Theodericus')
        
        naam = Name('Lodewijk XVIII')   
        self.assertEqual(naam.guess_normal_form2(), 'Lodewijk XVIII')
        
        s = """<persName> <name type="voornaam">Trijn</name> <name type="intrapositie">van</name> <name type="geslachtsnaam">Leemput</name></persName>"""
        naam = Name().from_string(s)
        
        self.assertEqual(naam.guess_normal_form(), 'Leemput, Trijn van')
        self.assertEqual(naam.guess_normal_form2(), 'Trijn van Leemput')
        
        n5 = Name('Piet Gerbrandy', geslachtsnaam='Gerbrandy')
        self.assertEqual(n5.guess_normal_form(), 'Gerbrandy, Piet')
        self.assertEqual(n5.guess_normal_form2(), 'Piet Gerbrandy')
        
#        n6 = Name('Piet Gerbrandy', geslachtsnaam='Piet')
#        n6._tokenize()
#        self.assertEqual(n6.guess_normal_form(), 'Piet Gerbrandy')
#        self.assertEqual(n6.guess_normal_form2(), 'Gerbrandy Piet')
        
        n = Name('Hermansz')
        self.assertEqual(n.guess_normal_form(), 'Hermansz')
        self.assertEqual(n.geslachtsnaam(), 'Hermansz')
        
        n = Name('Ada, van Holland (1)')
        self.assertEqual(n.guess_normal_form(), 'Ada, van Holland')
       
        n = Name('Hees - B.P. van') 
        self.assertEqual(n.guess_normal_form(), 'Hees - B.P. van')
        
        n = Name('Hees - B.P. van (1234-1235)') 
        self.assertEqual(n.guess_normal_form(), 'Hees - B.P. van')
       
        n = Name('Hoeven, Abraham des Amorie van der (1)')
        
        self.assertEqual(n.guess_normal_form(), 'Hoeven, Abraham des Amorie van der')
        self.assertEqual(n.guess_normal_form2(), 'Abraham des Amorie van der Hoeven')
        
        n = Name('Schepper, Gerhard Antoni IJssel de')
        self.assertEqual(n.guess_normal_form(), 'Schepper, Gerhard Antoni IJssel de')
        
        
    def test_volledige_naam(self):
        n = Name(voornaam='Jelle')
        self.assertEqual(n.get_volledige_naam(),'Jelle')
        n.guess_geslachtsnaam()
        self.assertEqual(n.get_volledige_naam(),'Jelle')
        n = Name().from_string("""<persName>
<name type="voornaam">Hendrik IV</name>
</persName>""")
        self.assertEqual(n.get_volledige_naam(), 'Hendrik IV')
        
        naam = Name(voornaam='Hendrik IV')
        self.assertEqual(naam.get_volledige_naam(), u'Hendrik IV')
   
    def test_fix_capitals(self):
        self.assertEqual(fix_capitals('Jean-Jules'), 'Jean-Jules')
        self.assertEqual(fix_capitals('Johan VIII'), 'Johan VIII')
        self.assertEqual(fix_capitals('Johan III'), 'Johan III')
        self.assertEqual(fix_capitals('Fabricius/Fabritius'), 'Fabricius/Fabritius')
        self.assertEqual(fix_capitals("L'OYSELEUR") , "l'Oyseleur")
        self.assertEqual(fix_capitals(u'Schepper, Gerhard Antoni IJssel de'), u'Schepper, Gerhard Antoni IJssel de')
                         
        
    def test_html2unicode(self): 
        s = u'M&ouml;törhead'
        n = Name(s)
        self.assertEqual(n.volledige_naam(), u'Mötörhead')
        
        #this shoudl not be here, but under a separate test for the utility functions in common
        self.assertEqual(html2unicode('&eacute;'), u'é')
        self.assertEqual(html2unicode('S&atilde;o'), u'São')
    def test_sort_key(self):
        s ='<persName>Jelle <name type="geslachtsnaam">Gerbrandy</name></persName>'
        n = Name().from_string(s)
        self.assertEqual(n.sort_key()[:15], 'gerbrandy jelle')

        s ='<persName>Jelle <name type="geslachtsnaam">Éerbrandy</name></persName>'
        n = Name().from_string(s)
        self.assertEqual(n.sort_key()[:15], 'eerbrandy jelle')

        n = Name(u'São Paolo')
        self.assertEqual(n.geslachtsnaam(), 'Paolo') # Automatically guessed
        self.assertEqual(n.sort_key().split()[0], 'paolo')
        
        n = Name('(Hans) Christian')
        self.assertEqual(n.sort_key().split()[0], 'christian')
        
        n =Name(u'Løwencron')
        self.assertEqual(n.sort_key().split()[0], 'loewencron')
        
        n = Name(u'?, Pietje')
        self.assertTrue(n.sort_key() > 'a', n.sort_key())    
        
        n = Name("L'Hermite")    
        self.assertTrue(n.sort_key().startswith('herm'))
        
        n = Name("La Hermite")    
        self.assertTrue(n.sort_key().startswith('herm')), n.sort_key()
        
        n = Name(u'Löwel')
        self.assertTrue(n.sort_key().startswith('lo')), n.sort_key()
        
        n = Name("1'Aubepine, Charles de") #this name starts with the numeral "1"
        self.assertTrue(n.sort_key().startswith('au')), n.sort_key()
        
        n = Name(u'Géo d\'Aconit')
        self.assertTrue(n.sort_key().startswith('aco'))
        
        s ='<persName>Samuel <name type="geslachtsnaam">Beckett</name></persName>'
        n1 = Name().from_string(s)
        s ='<persName>Beckett, Samuel</persName>'
        n2 = Name().from_string(s)
        self.assertEqual(n1.sort_key(), n2.sort_key())
        
    def test_spaces_in_xml(self):
        n = Name(voornaam='Jelle', geslachtsnaam='Gerbrandy')
        s = '<persName><name type="voornaam">Jelle</name> <name type="geslachtsnaam">Gerbrandy</name></persName>'
        self.assertEqual(n.to_string(), s)

#      
    def test_initials(self):
        self.assertEqual(Name('P. Gerbrandy').initials(), 'PG')
        self.assertEqual(Name('Engelmann, Th.W.').initials(), 'TWE')
        self.assertEqual(Name('Borret, Prof. Dr. Theodoor Joseph Hubert').initials(), 'TJHB')
        self.assertEqual(Name('Hoeven, Abraham des Amorie van der (1)').initials(), u'AAH')
        
    def test_soundex_nl(self):
        s ='<persName>Jelle <name type="geslachtsnaam">Gerbrandy</name></persName>'
        n = Name().from_string(s)
        self.assertEqual(set(n.soundex_nl(length=5)), set(['g.rpr', 'j.l']))
        s ='<persName>Jelle <name type="geslachtsnaam">Scholten</name></persName>'
        
        #now that we have computed the soundex_nl, its value should be cached
        n = Name().from_string(s)
        
        self.assertEqual(n.soundex_nl(length=5), ['sg.lt', 'j.l'])
        self.assertEqual(set(Name('janssen, hendrik').soundex_nl(group=1)), set(['j.ns', '.tr.']))
        self.assertEqual(Name('aearssen-walte, lucia van').soundex_nl(group=1), Name('aearssen,walte, lucia van').soundex_nl(group=1))
#        self.assertEqual(Name('Jhr. Mr. K').soundex_nl(), ['k'])
        self.assertEqual(set(Name('janssen, hendrik').soundex_geslachtsnaam()), set([u'j.ns']))
        
    def test_init(self):
        
        naam = Name(
            prepositie=None,
            voornaam=None,
            intrapositie='van het',
            geslachtsnaam='Reve',
            postpositie=None,
            volledige_naam='Gerard van het Reve',
            )
        
        self.assertEqual(naam.volledige_naam(), 'Gerard van het Reve')
        self.assertEqual(naam.geslachtsnaam(), 'Reve')
        naam = Name(
            prepositie='dhr.',
            voornaam='Gerard',
            intrapositie='van het',
            geslachtsnaam='Reve',
            postpositie='schrijver',
            volledige_naam='dhr. Gerard van het Reve, schrijver',
            )
        
        self.assertEqual(naam.prepositie(), 'dhr.')
        self.assertEqual(naam.voornaam(), 'Gerard')
        self.assertEqual(naam.intrapositie(), 'van het')
        self.assertEqual(naam.geslachtsnaam(), 'Reve')
        self.assertEqual(naam.postpositie(), 'schrijver')
        self.assertEqual(naam.geslachtsnaam(), 'Reve')
    
#    def test_name_parts(self):
#        name_parts = Name('abc. DE. F;dk. Genoeg-Van')._name_parts()
#        self.assertEqual(name_parts, [u'abc.', u'DE.', 'F;dk.', 'Genoeg-Van'])

    def test_geslachtsnaam_guess(self):
        problematic_names = ['abc. DE. F;dk. Genoeg-Van']
        for namestr in problematic_names:
            name = Name(namestr)
            should_be = re.sub('<[^>]+>', '', name.to_string())
            self.assertEqual(namestr, should_be)


    def test_contains_initials(self):
        self.assertEqual(Name('J.K. Rowling').guess_geslachtsnaam(), 'Rowling')
        self.assertEqual(Name('J.K. Rowling').contains_initials(), True)
        self.assertEqual(Name('Th.D. de Rowling').contains_initials(), True)
        self.assertEqual(Name('Rowling, Jan').contains_initials(), False)
        self.assertEqual(Name('Rowling, J.').contains_initials(), True)
    
    def test_guess_constituents(self):
        
        #name of the form family_name, given_name 
        s1 ='<persName><name type="geslachtsnaam">Beckett</name>, <name type="voornaam">Samuel</name></persName>'
        s2 ='Beckett, Samuel'
        self.assertEqual(etree.tostring(Name(s2)._guess_constituents()), s1) #@UndefinedVariable
        
        #test round trip
        self.assertEqual(etree.tostring(Name().from_string(s1)._guess_constituents()), s1) #@UndefinedVariable
        
        #a simple normal name
        s1 ='<persName><name type="voornaam">Samuel</name> <name type="geslachtsnaam">Beckett</name></persName>'
        s2 ='Samuel Beckett'
        self.assertEqual(etree.tostring(Name(s2)._guess_constituents()), s1) #@UndefinedVariable
       
        #test round trip
        self.assertEqual(etree.tostring(Name().from_string(s1)._guess_constituents()), s1) #@UndefinedVariable

        #intrapositions 
        s1 ='Hugo de Groot'
        s2 ='<persName><name type="voornaam">Hugo</name> <name type="intrapositie">de</name> <name type="geslachtsnaam">Groot</name></persName>'
        self.assertEqual(etree.tostring(Name(s1)._guess_constituents()), s2) #@UndefinedVariable

        s1 = 'Marie Bakker-de Groot'
        s2 ='<persName><name type="voornaam">Marie</name> <name type="geslachtsnaam">Bakker-de Groot</name></persName>'
        self.assertEqual(etree.tostring(Name(s1)._guess_constituents()), s2) #@UndefinedVariable
        
        s1 = 'Arien A'
        s2 ='<persName><name type="voornaam">Arien</name> <name type="geslachtsnaam">A</name></persName>'
        self.assertEqual(etree.tostring(Name(s1)._guess_constituents()), s2) #@UndefinedVariable
    
    def test_insert_consituent(self):
        s1 ='<persName>Hugo <name type="intrapositie">de</name> <name type="geslachtsnaam">Groot</name></persName>'
        s2 ='<persName><name type="voornaam">Hugo</name> <name type="intrapositie">de</name> <name type="geslachtsnaam">Groot</name></persName>'
        s3 ='<persName>Hugo de Groot</persName>'
        s4 ='<persName>Hugo <name type="intrapositie">de</name> Groot</persName>'
        name = Name().from_string(s1)
        text = name.to_xml().text
        #check sanity
        self.assertEqual(text,'Hugo ')
        m = re.match('Hugo', text)
        name._insert_constituent('voornaam', m)
        self.assertEqual(name.to_string(), s2)
        
        name = Name().from_string(s3)
        text = name.to_xml().text
        m = re.search('de', text)
        name._insert_constituent('intrapositie', m)
        self.assertEqual(name.to_string(), s4)

    def test_constituent_tokens(self):    
        s1 = 'koning Karel VI'
        t1 = [(u'koning', TYPE_TERRITORIAL), (u'Karel', TYPE_GIVENNAME), (u'VI', TYPE_GIVENNAME)]
        self.assertEqual(str(Name(s1)._guess_constituent_tokens()), str(t1))

        s1 = 'Karel VI'
        t1 = [(u'Karel', TYPE_GIVENNAME), (u'VI', TYPE_GIVENNAME)]
        self.assertEqual(str(Name(s1)._guess_constituent_tokens()), str(t1))
        
       
        s1 = 'A.R. Bastiaensen CM'
        t1 = [(u'A.', TYPE_GIVENNAME), (u'R.', TYPE_GIVENNAME), (u'Bastiaensen', TYPE_FAMILYNAME),(u'CM', TYPE_FAMILYNAME)]
        self.assertEqual(Name(s1)._guess_constituent_tokens(), t1)
              
        s1 = 'Willem III, graaf van Nassau'
        t1 = [('Willem', TYPE_GIVENNAME), ('III', TYPE_GIVENNAME), (',', ','), ('graaf', TYPE_TERRITORIAL), ('van', TYPE_TERRITORIAL), ('Nassau', TYPE_TERRITORIAL)]
        x = Name(s1)._guess_constituent_tokens()
        y = t1
        self.assertEqual(x, y)
        
        s1 = 'Amelia van Nassau-Dietz'
        t1 = [('Amelia', 'voornaam'), ('van', 'intrapositie'), ('Nassau', 'geslachtsnaam'), ('-', 'geslachtsnaam'), ('Dietz', 'geslachtsnaam')]
        self.assertEqual(Name(s1)._guess_constituent_tokens(), t1)
       
        s1 = 'Johan IV van Nassau-Dillenburg' 
        t1 = [('Johan', 'voornaam'), ('IV', 'voornaam'), ('van', 'intrapositie'), ('Nassau', 'geslachtsnaam'), ('-', 'geslachtsnaam'), ('Dillenburg', 'geslachtsnaam')]
        self.assertEqual(Name(s1)._guess_constituent_tokens(), t1)
        
        s1 = 'Maurits Lodewijk van Nassau La Lecq'
        t1 = [('Maurits', 'voornaam'), ('Lodewijk', 'voornaam'), ('van', 'intrapositie'), ('Nassau', 'geslachtsnaam'), ('La', 'geslachtsnaam'), ('Lecq', 'geslachtsnaam')]
        self.assertEqual(Name(s1)._guess_constituent_tokens(), t1)
        
        s1 = u'Mencía de Mendoza y Fonseca'
        t1 = [(u'Menc\xeda', 'voornaam'), (u'de', 'intrapositie'), (u'Mendoza', 'geslachtsnaam'), (u'y', 'geslachtsnaam'), (u'Fonseca', 'geslachtsnaam')]
        self.assertEqual(Name(s1)._guess_constituent_tokens(), t1)
        
        s1 = u'Wilhelmina van Pruisen - prinses van Oranje-Nassau'
        t1 = [('Wilhelmina', 'geslachtsnaam'), ('van', 'intrapositie'), ('Pruisen', 'geslachtsnaam'), ('-', '-'), ('prinses', 'territoriale_titel'), ('van', 'territoriale_titel'), ('Oranje', 'territoriale_titel'), ('-', '-'), ('Nassau', 'territoriale_titel')]
        self.assertEqual(Name(s1)._guess_constituent_tokens(), t1)
        
        s1 = u'Henriette Adriana Louise Flora d\'Oultremont de Wégimont'
        t1 = [(u'Henriette', 'voornaam'), (u'Adriana', 'voornaam'), (u'Louise', 'voornaam'), (u'Flora', 'voornaam'), (u"d'", 'geslachtsnaam'), (u'Oultremont', 'geslachtsnaam'), (u'de', 'intrapositie'), (u'W\xe9gimont', 'geslachtsnaam')]
        self.assertEqual(Name(s1)._guess_constituent_tokens(), t1)
       
        s1 = u'Hendrik de Graaf' 
        t1 = [('Hendrik', 'voornaam'), ('de', 'intrapositie'), ('Graaf', 'geslachtsnaam')]
        self.assertEqual(Name(s1)._guess_constituent_tokens(), t1)
        
        s1 = u'Hendrick graaf van Cuyck'
        t1 = [('Hendrick', 'geslachtsnaam'), ('graaf', 'territoriale_titel'), ('van', 'territoriale_titel'), ('Cuyck', 'territoriale_titel')]
        self.assertEqual(Name(s1)._guess_constituent_tokens(), t1)
       
        s1 = 'Hoeven, Abraham des Amorie van der' 
        t1 = [('Hoeven', 'geslachtsnaam'), (',', ','), ('Abraham', 'voornaam'), ('des', 'intrapositie'), ('Amorie', 'geslachtsnaam'), ('van', 'intrapositie'), ('der', 'intrapositie')]
        self.assertEqual(Name(s1)._guess_constituent_tokens(), t1)
        
        s1 = 'Schwartzenberg, Johan Onuphrius thoe'
        t1 = [('Schwartzenberg', 'geslachtsnaam'), (',', ','), ('Johan', 'voornaam'),('Onuphrius', 'voornaam'), ('thoe', 'intrapositie')]
        self.assertEqual(Name(s1)._guess_constituent_tokens(), t1)
        
    def test_tokenize(self):
        s1 ='<persName>Hugo <name type="intrapositie">de</name> <name type="geslachtsnaam">Groot</name></persName>'
        t1 = [Token('Hugo', None, tail=' '), Token('de', 'intrapositie', tail=' '), Token('Groot', 'geslachtsnaam')]
        s2 ='<persName><name type="voornaam">Hugo</name> <name type="intrapositie">de</name> <name type="geslachtsnaam">Groot</name></persName>'
        t2 = [Token('Hugo', 'voornaam', tail=' '), Token('de', 'intrapositie', tail=' '), Token('Groot', 'geslachtsnaam')]
        s3 ='<persName>Hugo de Groot</persName>'
        t3 = [Token('Hugo', None, tail=' '), Token('de', None, tail=' '), Token('Groot', None)]
       
        s4 = '<persName>Groot, Hugo</persName>'
        t4 = [Token('Groot', None), Token(',', None, tail=' '), Token('Hugo', None)]
        
        s5 = '<persName>H.P. de Groot</persName>'
        t5 = [Token('H.', None), Token('P.', None, tail=' '), Token('de', None, tail=' '), Token('Groot', None)]
        
        self.assertEqual(Name().from_string(s1)._tokenize(), t1)
        self.assertEqual(Name().from_string(s1)._tokenize()[0].tail(), ' ')
        self.assertEqual(Name().from_string(s1)._tokenize()[1].tail(), ' ')
        self.assertEqual(Name().from_string(s1)._tokenize()[2].tail(), '')
        self.assertEqual(Name().from_string(s2)._tokenize(), t2)
        self.assertEqual(Name().from_string(s3)._tokenize(), t3)
        self.assertEqual(Name().from_string(s4)._tokenize(), t4)
        self.assertEqual(Name().from_string(s5)._tokenize(), t5)
       
        self.assertEqual(etree.tostring(Name()._detokenize(t1)), s1) #@UndefinedVariable
        self.assertEqual(etree.tostring(Name()._detokenize(t2)), s2) #@UndefinedVariable
        self.assertEqual(etree.tostring(Name()._detokenize(t3)), s3) #@UndefinedVariable
        self.assertEqual(etree.tostring(Name()._detokenize(t4)), s4) #@UndefinedVariable
        self.assertEqual(etree.tostring(Name()._detokenize(t5)), s5) #@UndefinedVariable
        
        s = '<persName>Beter (met haakjes)</persName>'
        t = [Token('Beter', None, tail= ' '), Token('(', tail=''), Token('met', tail=' '), Token('haakjes'), Token(')', None)]
        self.assertEqual(Name().from_string(s)._tokenize(), t)
        self.assertEqual(etree.tostring(Name()._detokenize(t)), s) #@UndefinedVariable
       
        s = '<persName>C.H.Veenstra</persName>'
        t = [Token('C.', None), Token('H.', None), Token('Veenstra', None)]
        self.assertEqual(Name().from_string(s)._tokenize(), t)

        self.assertEqual(Name("l'Abc")._tokenize(), [(u"l'", None), ('Abc', None)])
                         
def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite(NameTestCase ),
        ))

if __name__=='__main__':
#    unittest.main(defaultTest='NameTestCase.test_constituent_tokens')

    unittest.main()
