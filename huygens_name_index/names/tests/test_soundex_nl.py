#! /usr/bin/python    
#encoding=utf-8
import unittest
from names.name import Name 
from names.soundex import soundex_nl, soundexes_nl
from names.common import TUSSENVOEGSELS

def soundex_nl1(s, length=4):
    return soundex_nl(s, length, group=1)

def soundex_nl2(s, length=-1):
    return soundex_nl(s, length, group=2)

SAME_SOUNDEX = [
        #these names shoudl generate the same soundex expression
        ('Abraham', 'Abram'),
        ('Kluyt', 'kluit'),
        ('Kluyt,', 'kluit'),
        ('Kluijt', 'kluit'),
        ('Gerbrandij', 'Gerbrandy'),
        ('Eijck', 'ik'),
        ('Eijck', 'ik'),
        ('fortuin', 'fortuijn'), 
        ('fortuyn', 'fortuijn'), 
        ('kwak','quack'),
        ('quintus', 'kwintus'),
        ('riks', 'rix'),
        ('theodorus', 'teodorus'),
        ('meijer', 'meyer'),
        ('meier', 'meyer'),
        ('mijer', 'meier'),
        ('wildt', 'wild'), 
        ('wilt', 'wild'), 
        ('wilt', 'wild'), 
        ('françois', 'fransoys'),
        ('françois', 'francois'),
        ('éé', 'e'),
        ('ouw', 'auw'),
        ('ou', 'au'),
        ('haer', 'haar'),
        ('u', 'uu'),
        ('Catharina', 'Katarina'),
        ('Catharina', 'Catharine'),
        ('Theresa', 'Teresa'),
        ('Aangenend',
            'Aangenendt', 
            'Aangenent', 
#                'Aengenant', 
            'Aengenend', 
            'Aengenendt', 
            'Aengenent',  
            'Agenent',
            'Angeneind', 
            'Angenend',
            'Angenendt',
            'Angenent',
        ),
        (
            'Nooteboom',
            'Nootenboom',
            'Noteboom',
            'Notenboom',
#                'Neuteboom',
#                'Neutenboom',
#                'Notebomer',
#                'Notenbomer',
            'Nottebaum',
            'Nottebohm',
            'Notteboom',
#                'Nussbaum',
#                'Nussbaumer',
#                'Nuszbaum',
#                'Nuszbaumer',
        ), 
        ('bosma',
         'boschma',
         ),
         ("O'Connor", 'Connor'),
         ('Ryszard', 'Richard'),
         ('Kapuściński', 'Capusinski'),
         ('Kabeljauw', 'Cabeliau'),
         ('Christiaans', 'Christiaens'), 
         ('Klouk', 'Kloek'),
         ('Queillerie' , 'Quellerie'), 
         ('Nieuwland', 'Nieuland'),
         ('Dyserink', 'Dijserink'),
         ('Dyserink', 'Dijserinck'),
#         (u'Kloek', 'Kluk'),
         ('Pieterszoon', 'Pietersz.'),
         ('Johannes', 'Jan'),
         ('Klerk', 'Klerq'),
         ('Clerq', 'Clercq'),
         ('nieupoort', 'nypoort'),
         ('wyntges', 'wijntjes'),
         ('utenhove', 'uytenhove'),
         ('uytenbogaert', 'Wtenbogaert'),
         ('surenhusius', 'surenhuys'),
        ]
 
class SoundexNLTestCase(unittest.TestCase):

    def test_soundex_nl1(self):
        self.assertEqual(soundex_nl1('Scholten', length=5), 'sg.lt')
        n1 = Name('Uyl')
        n2 = Name('Uijl')
        n3 = Name('Uil')
        n4 = Name('Yl')
        self.assertEqual(n1.soundex_nl(length=5), ['.l'])
        self.assertEqual(n2.soundex_nl(length=5), ['.l'])
        self.assertEqual(n3.soundex_nl(length=5), ['.l'])
        self.assertEqual(n4.soundex_nl(length=5), ['.l'])
        
        self.assertEqual(Name('AAA').soundex_nl(), ['.'])
        self.assertEqual(Name('Quade').soundex_nl(), ['k.t'])
        self.assertEqual(Name('Quack').soundex_nl(), ['k.k'])
        self.assertEqual(Name('kwak').soundex_nl(), ['k.k'])
        self.assertEqual(Name('kwik en kwak').soundex_nl(), ['k.k', ])
        self.assertEqual(Name('rhood').soundex_nl(), ['r.t'])
        self.assertEqual(Name('zutphen').soundex_nl(), ['s.tf'])
        self.assertEqual(Name('Willem').soundex_nl(), ['f.l.'])

        #diacritics?
        self.assertEqual(soundex_nl1('wél'), 'f.l') 
        self.assertEqual(soundex_nl1('bosma'), soundex_nl1('boschma')) 
        self.assertEqual(Name('Pius IX').soundex_nl(), ['p.s', ])
        for ls in SAME_SOUNDEX:
            n1 = ls[0]
            s1 = soundex_nl1(n1)
            for n2 in ls[1:]:
                s2 = soundex_nl1(n2)
                self.assertEqual(s1, s2, '%s=>%s ::: %s=>%s' %( n1, s1, n2, s2))
 
    def test_soundex_nl2(self):
        # group 2 is de "fonetische soundex"       
        #c
        for s, wanted in [
            #examples of soundex expressions
            #the first item of the tuple is the input, the second the expected soundex
            ('Huis', 'huis'),
            ('Huys', 'huis'),
            ('goed', 'got'),
            ('eijck', 'ik'),
            #ei, eij, ij, ey, y, i
            ('ijck', 'ik'),
            ('ildt', 'ilt'), 
            ('ild', 'ilt'), 
            ('til', 'til'),
            ('buyt', 'buit'),
            ('s?t', 'st'),
            ('meijer', 'mier'),
            ('Stámkart', 'stamkart' ),
            ('Stáamkart', 'stamkart' ),
            ('broeksz', 'brok'), #??
            ('æbel', 'abel'),
            ('a', 'a'),
            ('i', 'i'),
            ('Heer', 'her'),
            ]:
            self.assertEqual(wanted, soundex_nl2(s), '%s - %s - %s'  % (s, wanted, soundex_nl2(s)))
            
            
        #THESE GET THE SAME SOUNDEXES
        for ls in SAME_SOUNDEX:
            n1 = ls[0]
            s1 = soundex_nl2(n1)
            for n2 in ls[1:]:
                s2 = soundex_nl2(n2)
                self.assertEqual(s1, s2, '%s=>%s ::: %s=>%s' %( n1, s1, n2, s2))
   
    def test_different_soundexes(self):
        for n1, n2 in [
            #these strings shoudl generate different soundex expression
            ('x', 'y'),
            ('gaag', 'goch'),
#            ('leeuwen', 'leuven'),
            ]:
            s1 = soundex_nl2(n1)
            s2 = soundex_nl2(n2)
            self.assertNotEqual(s1, s2, '%s=>%s ::: %s=>%s' %( n1, s1, n2, s2))
            
    def test_soundexes_nl(self):
        self.assertEqual(soundexes_nl('Samuel Beckett', length=-1), ['beket', 'samul'])
        self.assertEqual(soundexes_nl('don?er') , ['doner'])
        self.assertEqual(soundexes_nl('don?er', wildcards=True) , ['don?er'])
        self.assertEqual(soundexes_nl('don*er', wildcards=True) , ['don*er'])
        self.assertEqual(soundexes_nl('willem I' ) , ['filem' ])
        self.assertEqual(soundexes_nl('heer' ) , [])
        self.assertEqual(soundexes_nl('jhr.' ) , [])
        self.assertEqual(soundexes_nl('van', filter_custom=TUSSENVOEGSELS ) , [])
        self.assertEqual(soundexes_nl('annie m.g. schmidt', ) , ['m','ani', 'g', 'smit'])
    
    def test_if_soundexes_nl_returns_unicode(self):
        self.assertEqual(type(soundexes_nl('Samuel Beckett')[0]), type(''))
        
    def test_bioport_usecases(self):
        """in the biographical portal,
        soundexes_nl is used with the following arguments:
            soundexes_nl(s, group=2, length=20, filter_initials=True, filter_stop_words=False)
        """
        bioport_soundex = lambda s: soundexes_nl(s, group=2, length=20, filter_initials=True, filter_stop_words=False)
        self.assertEqual(set(bioport_soundex('Pius IX')), set(['pius', 'IX']))
        
class IdealWorldNLTestCase(unittest.TestCase):
    """ """
    def test1(self):
        ls_names = (
            ('Aartsen','Aardze',
                #'Aarssee',
                'Aartse','Aartsen','Aartze',
                #'Aerts',
                ),
            ('Achterveld','Achterveld',
             #'Achteveld',
             'Agterveld',
             #'Agteveld',
             ),
            ('Achthoven','Achthoven','Achtoven',),
            ('Akkerman','Ackerman','Ackermann',),
            (
             #'Alderding',
             'Alberdingh','Alberdingk',
             #'Albering',
             #'Alderding',
             ),
            ('Altena','Altena','Altenaar',
             #'Altona',
             ),
            ('Apeldoorn','Apeldoorn','Appeldoorn',),
            ('Arendsen','Arends','Arendse','Arendsen','Arentsen',),
            ('Asch','As','Asch',),
            ('Baart','Baard','Baardt','Baart',),
            ('Barbé','Barbe','Barbé',),
            ('Barendsen','Barendsen','Barentsen',
               # 'Berendsen','Berentsen',
               ),
            ('Bedum','Bedum','Beedem',),
            ('Beijer',
             #'Beijen',
             'Beijer','Bijer',),
            ('Bekker','Becker',
             #'Beckers',
             ),
            ('Berenkamp','Beerekamp','Beerenkamp',),
            ('Berg','Berg','Bergh',),
            ('Berkhof','Berkhof','Berkhoff',
                #'Birkhof','Birkhoff','Birkhoven',
                ),
            ('Besançon','Besanson','Besançon',),
            ('Beuken','Beuke','Beuken',),
            ('Bijleveld','Bijleveld','Bijlevelt',),
            ('Bilt','Bild','Bildt','Bilt',),
            ('Blanken','Blanke','Blanken',),
            ('Blankenstein','Blankensteijn','Blankenstein','Blankestijn',),
            ('Blauwendraad','Blaauwendraad','Blauwedraad','Blauwendraad','Blauwendraat','Blouwendraad',),
            ('Bleijenberg','Bleijenberg','Bleijenburg','Blijenberg',),
            ('Blokland','Blokland',
                 #'Bloklander',
                 ),
            ('Boersen','Boers','Boersen','Boerssen','Boertsen',),
            ('Bos','Bos','Bosch',),
            ('Boshuizen','Boshuizen','Boshuyzen',),
            ('Bosveld','Bosveld','Bosvelt',),
            ('Bouwhuizen','Bouhuijs','Bouhuijzen','Bouwhuizen',),
        ('Broekhuizen','Broekhuijsen','Broekhuis','Broekhuizen',),
        ('Cornelissen','Cornelisse','Cornelissen',),
        ('Dorrestein','Dorrenstijn','Dorresteijn','Dorrestein','Dorresteyn','Dorrestijn',
            #'Dorsteen',
            ),
        ('Driftakker','Driftacker','Driftakker',),
        ('Droffelaar','Droeffelaar','Droffelaar',),
        ('Duin','Duijn','Duin','Duine','Duinen',),
#        ('Eden',
            #'Ee',
            #'Eede',
#            'Eeden',),
        ('Egdom','Echdom','Egdom',),
        ('Eindhoven','Eijndthoven','Eindhoven',),
        ('Elbertsen','Elberse','Elbersen','Elbertse','Elbertsen','Elbertze',),
        ('Elders','Elder','Elders',),
        ('Endendijk','Endedijk','Endendijk',),
        ('Es','Es','Esch',),
        ('Essenberg','Essenberg','Essenburg',),
#        ('Ettikhoven','Ettekhoven','Ettekoven',),
        ('Evertsen','Evers','Everse','Everts','Evertse','Evertsen','Evertze',),
        #ie = ee
#        ('Bredee','Bredee','Bredie','Bredius','Bredée','Briedé','Brodie',),
        #
#        ('Breemer','Breemen','Breemer','Breemert','Breenen','Bremer','Bremert',),
        #-s at the end
        ('Broers',
            #'Broere',
            'Broers','Broerze',),
        #ts -> s
        ('Butselaar',
            #'Busselaar',
            'Butselaar','Butzelaar',),
        #st -> s
        ('Dijssel','Deijsel','Deijssel',
            #'Deijstel',
            'Deyssel','Dijssel','Dyssel',),
        ('Daatselaar','Daadselaar','Daadzelaar',
            #'Daaselaar',
            'Daatselaar','Daatzelaar',
            #'Daselaar','Dazelaar',
            ),
        #m -> n
#        ('Donselaar','Dompselaar','Dompzelaar','Domselaar','Donselaar',),
        ('Bruin','Bruijn','Bruijne','Bruin',
            #'Bruins',
            'Bruyn',),
        ('Fluit','Fluijt','Fluit','Fluyt',),
        ('Fokken','Focken','Fokke','Fokken','Fokkens',
            #'Fokker',
            ),
        ('Fontijn','Fonteijn','Fontijn','Fontijne',),
        ('Franken','Franck','Francken','Frank','Franke','Franken',),
        ('Frankrijker','Frankrijker','Vrankrijker',),
        ('Gallenkamp','Galenkamp','Gallenkamp',),
        ('Geerestein','Geerestein','Gerestein',),
        ('Geitenbeek','Geijtenbeek','Geitenbeek','Geytenbeek','Gijtenbeek',),
        ('Gerritsen','Gerrits','Gerritse','Gerritsen',),
        ('Geurtsen','Geurts','Geurtse','Geurtsen',),
        ('Graaf','Graaf','Graaff',),
        ('Groenenstein',
            #'Goenensteyn',
            'Groenensteijn','Groenenstein','Groenenstijn','Groenesteijn','Groenestein','Groenestijn',),
        ('Groenewoud','Groenewold','Groenewoud',),
        ('Hagen','Haage','Hage','Hagen',),
        ('Hagendoorn','Hagedoorn','Hagendoorn',),
        ('Hamersveld','Hamersfeld','Hamersveld',),
        ('Hansen','Hansen','Hanssen',),
        ('Hardeveld','Hardeveld','Hardevelt',),
        ('Harmsen','Harms','Harmsen',
            #'Hermse','Hermsen',
            ),
        ('Harselaar','Harselaar',
            #'Haselen','Hasselaar','Hazalaar',
            ),
        ('Harskamp','Harskamp','Hartskamp',),
        ('Hassink','Hassing','Hassink',),
        ('Hattum','Hattem','Hattum',),
#        ('Heerschop','Heerschap','Heerschop',),
        ('Hees','Hees',
            #'Heijs','Heis',
            ),
        ('Heiden','Heide','Heiden',
            #'Heijdem',
            'Heijden',
            #'Heijen',
            'Heyden',),
        ('Helmersen',
            #'Helmer',
            'Helmers',
            #'Helmesse','Helms','Helmus',
            ),
        ('Helsdingen','Helsding','Helsdingen',
            #'Helsdinger' ,
            ),
        ('Hendriksen','Hendricks','Hendriks','Hendrikse','Hendriksen','Hendriksse','Hendrikx',),
        ('Hermans',
            #'Herman',
            'Hermans','Hermanssen',),
        ('Herwaarden',
            #'Herrewaarden',
            'Herwaarden',),
        ('Hoed','Hoed','Hoedt',),
        ('Hoenderdal','Hoenderdaal','Hoenderdal',),
        ('Hof','Hof','Hoff',),
        ('Hofman','Hoffman','Hoffmann','Hofman','Hofmann',),
        ('Jansen','Janse','Jansen','Janssen','Janssens','Jansz','Janze','Janzen',),
        ('Jong','Jong','Jonge','Jongh',),
        ('Karelsen','Carels','Carelse','Carelsen',
            #'Carilse',
            'Karelse','Karelsen',),
        ('Karssenmeijer','Karssemeijer','Karssemeyer','Karssenmeijer','Karssenmeyer',
            #'Kersemeijer','Kerssemeijer','Kerssemeyer','Kerssenmeijer','Kerssenmeyer',
            ),
        ('Kaufeld','Cauffeld','Kauffelt','Kouffeld',),
        ('Keizer','Keijser','Keijzer','Keizer','Kijser',),
        ('Klaasen','Claas','Claassen','Claessens',
            #'Claeyssens',
            'Klaasen','Klaasse','Klaassen',),
        ('Klein','Kleijn','Klein','Klijn',),
        ('Klooster','Clooster','Klooster',),
        ('Knoppers','Knoppers',
            #'Knoppert',
            'Knopperts',),
        ('Koenen','Coenen',),
        ('Koerten','Coerten',
            #'Koersen',
            #'Koerts','Koertse',
            ),
        ('Kok','Cock','Kok',),
        ('Koljee','Coljee','Coljée',),
        ('Kooij','Kooi','Kooij','Kooy',),
        ('Kosijnsen',
            #'Cosijn','Cosijnse',
            #'Cousijn','Cousin',
            'Cozijnse',),
        ('Koterlet','Coterlet','Koterlet',),
        ('Kraaikamp','Kraaikamp',
            #'Kreijkamp','Krijkamp',
            ),
        ('Kruif','Cruijff','Kruif','Kruiff','Kruijf','Kruijff','Kruyf',),
        ('Kuijer','Kuier','Kuijer','Kuyer',),
        ('Kuiper','Kuijper',
            #'Kuijpers',
            #'Kuipers',
            ),
        ('Kuit','Kuijt','Kuit',),
        ('Lafebre','Lafebre','Lafèbre','Lafêbre',
            #'Lefebre','Lefrebre',
            ),
        ('Lagerweij','Lagerwei','Lagerweij',),
        ('Lakeman','Lakeman','Lakenman',),
        ('Lammertsen','Lamberts','Lammerse','Lammerts','Lammertse','Lammertsen',),
        ('Leeuwen','Leeuwe','Leeuwen',),
        ('Lente','Lent','Lente','Lenten',),
        ('Logtenstein','Lochtenstein','Logtensteijn','Logtenstein','Logtensteyn','Logtenstijn','Logtesteijn','Logtestein','Logtesteyn','Logtestijn',
            #'Lugtensteijn','Lugtensteyn','Lugtesteyn',
            ),
        ('Loodijk','Lodijk','Loodijk',),
        ('Looijen','Looije','Looijen',
            #'Looisen',
            ),
        ('Maanen','Maanen','Manen',),
        ('Maaren','Maar','Maare','Maaren','Maren',),
        ('Maasen','Maas','Maasen','Maassen',),
        ('Machielsen','Machielsen','Magielse','Magielsen',),
        ('Mansveld','Mansfeld','Mansfeldt','Mansfelt','Mansveld',),
        ('Martensen','Martens','Martense','Martensen',
            #'Martijnsen','Martijssen',
            ),
        ('Matthijssen','Matthijssen','Matthyssen',),
        ('Meerding','Meerding','Meerdink',
            #'Meering',
            ),
        ('Meeuwissen','Meeuwis','Meeuwissen',),
        ('Merkenich',
            #'Markenich',
            'Merckenich','Merkenich',
            #'Merkenij',
            ),
        ('Merkensteijn','Merkensteijn','Merkesteijn','Merkestein','Merkestijn',),
        ('Mets','Mets','Metz',),
        ('Natter','Natter',
            #'Nattert',
            ),
        ('Nieuwenhuizen','Nieuwenhuijs','Nieuwenhuijzen','Nieuwenhuis','Nieuwenhuizen',),
        ('Onwezen',
            #'Omwezen',
            'Onweezen',
            #'Onweis',
            #'Onwijs',
            ),
        ('Ooijen','Ooijen','Ooy','Ooyen',),
        ('Oostenbrugge','Oostenbrugge','Oostenbruggen',
            #'Osnabrugge','Osnabruggen',
            ),
#        ('Oostinje',
            #'Oosteenje','Oostinje','Osteenje',),
        ('Overhuizen','Overhuis','Overhuizen',
            #'Overhus','Overhuss',
            ),
        ('Papenburg','Paapenburg','Papenburg',),
        ('Rademaker','Raademaker','Rademaker',),
        ('Rauwendaal','Raauwendaal','Rouwendaal',),
        ('Reijerse','Reijerse','Reijersen','Reyerse','Rijerse',),
        ('Rijk','Rijk','Rijken',),
        ('Rijksen','Rijkens','Rijkse','Rijksen','Riksen',),
#        ('Ruijg','Ruig','Ruigt','Ruijg','Ruijgh','Ruijght','Ruijgt',),
        ('Ruiter','Ruijter','Ruiter','Ruyter',
            #u'Röijter',
            ),
#        ('Schaft','Schaft','Schagt',),
        ('Schaick','Schaick','Schaik',),
        ('Schalkx','Schalks','Schalkx',),
        ('Schoenmaker','Schoemaker','Schoenmaker',
            #'Schuhmacher',
            ),
#        ('Scholten','Schols','Scholte','Scholten',),
        ('Schoonoord','Schoonoord','Schoonoordt',),
        ('Schouten','Schoute','Schouten',),
        ('Seezink','Seesink','Seezink',),
        ('Slechtenhorst','Slechtenhorst','Slegtenhorst',),
        ('Smeeing','Smeeing','Smeink',
            #'Smienk','Smink',
            ),
        ('Smit','Schmidt','Schmit','Smid','Smit',
            #'Smits',
            ),
        ('Smorenburg','Smoorenburg','Smorenburg',),
        ('Stalenhoef','Staalenhoef','Stalenhoef','Stalenhoeff',),
#        ('Stiggelenbeek','Stiegelbeek','Stiggelenbeek','Tichelenbeek','Tiegelbeek','Tieghelbeek',),
        ('Stoutenburg','Stoutenberg','Stoutenburg',),
        ('Stralen','Straelen','Stralen',),
        ('Stuivenberg','Stuijvenberg','Stuivenberg',),
        ('Suijk','Suijck','Suijk','Suik','Suyk',),
#        ('Sukel','Sukel','Sukkel','Zeef','Zeeft',),
#        ('Swanink','Swanik','Swanink','Zwanik','Zwanink',),
#        ('Tammer','Tamer','Tammel','Tammelen','Tammelr','Tammer','Tammers',),
        ('Tesselhof','Tesselhof','Tesselhoff',),
#        ('Teunissen','Teunisen','Teunisse','Teunissen','Theunisse','Thone','Thonen','Thoone',),
        ('Veenendaal','Veenedaal','Veenendaal','Venendaal',),
        ('Veldhuizen','Veldhuijsen','Veldhuijzen','Veldhuis','Veldhuise','Veldhuisen','Veldhuize','Veldhuizen','Veldhuysen','Veldhuyzen',
            #'Velhuisen',
           # 'Velthuijse','Velthuijsen','Velthuisen','Velthuizen',
           ),
            
#        ('Vlier','Flier','Fliert',),
#        ('Vliet','Vlierd','Vliert','Vlierts','Vliet',),
#        ('Vlist','Vlis','Vlist',),
#        ('Vlug','Vlug','Vlugt',),
        ('Voorthuizen','Voorthuijsen','Voorthuijzen','Voorthuisen','Voorthuizen','Voorthuysen',
            #'Voorthuzen',
            ),
        ('Voskuilen','Voskuijl','Voskuijle','Voskuijlen','Voskuil','Voskuilen',),
        ('Vugt','Vught','Vugt',),
        ('Vulpen','Fulpe','Fulpen',
            #'Velpen',
            'Vulpen',),
        ('Weerenstein',
            #'Weerdesteijn','Weerdestein','Weerdesteyn','Weerdestijn',
            'Weerensteijn','Weerenstein','Weerensteyn','Weerenstijn','Weeresteijn','Weerestijn','Werensteijn','Werenstein','Werensteyn',),
#        ('Westeneng','Westeneng','Westening',),
#        ('Westenmeijer','Westemeijer','Westemeyer','Westemijer','Westenmeijer','Westenmeyer','Westermeijer','Westermijer','Westmeijer',),
        ('Westerveld','Westerveld','Westerveldt','Westervelt',),
        ('Westhof','Westhof','Westhoff',),
#        ('Wigtman','Wichmann','Wigman','Wigtman',),
        ('Willemsen','Willems','Willemse','Willemsen',),
        ('Winkelhuizen','Winkelhuisen','Winkelhuizen',),
        ('Wirtz','Wirtz','Wirz',),
#        ('Wolfswinkel','Wolfswinkel','Wolleswinkel',),
#        ('Woudenberg','Woudenberg','Wouwberg',),
        ('Woutersen','Wouters','Wouterse','Woutersen',),
#        ('Zijl','Zeijl','Ziel','Zieltjens','Zieltjes','Zijl',),
        ('Zoeten','Zoet','Zoete','Zoeten', 
            #'Zoeter',
            ),
        ('Zuilen','Zuijlen','Zuilen',),
        )    
        
        #test for soundex_nl1 and soundex_nl2
        for ls in ls_names:
            n1 = ls[0]
            s1 = soundex_nl1(n1)
            for n2 in ls[1:]:
                s2 = soundex_nl1(n2)
                self.assertEqual(s1, s2, '%s=>%s ::: %s=>%s' %( n1, s1, n2, s2))

        for ls in ls_names:
            n1 = ls[0]
            s1 = soundex_nl2(n1)
            for n2 in ls[1:]:
                s2 = soundex_nl2(n2)
                self.assertEqual(s1, s2, '%s=>%s ::: %s=>%s' %( n1, s1, n2, s2))

    def test2(self):
        #this we do *not* want to be equal
        ls_names = [
            ('ijck', 'IX'),
        ]
        for ls in ls_names:
            n1 = ls[0]
            s1 = soundex_nl2(n1)
            for n2 in ls[1:]:
                s2 = soundex_nl2(n2)
                self.assertNotEqual(s1, s2, '%s=>%s ::: %s=>%s' %( n1, s1, n2, s2))

if __name__ == "__main__":
    test_suite = unittest.TestSuite()
    tests = [SoundexNLTestCase, IdealWorldNLTestCase]
    for test in tests:
        test_suite.addTest(unittest.makeSuite(test))
    unittest.TextTestRunner(verbosity=2).run(test_suite)

    

"""
PLACHIER, PLACIER, PLACIET, PLAECYER, PLAEYSIER, PLAISIER,
PLAISIERS, PLAISIR(S), PLAIZIER, PLASIET, PLASIR, PLASSY,
PLAISYE, PLAISYET, PLATSIER, PLAYSIER, PLECIET(?), PLEISIE,
PLEITSIER, PLESIER, PLESIET(?), PLESSEY, PLESSIER, PLESSIET,
PLESSIS, PLESSY, PLESYT, PLESY, PLESYER, PLETSIER(S), PLETSIET,
PLETS(?), PLETZIER, PLEYSIER, PLEZE(?), PLEZI, PLEZIER, PLICIET,
PLISIER, PLISSIER, PLYCI(?), PLYSETS(?), PLYSIER, PLYSYER, PILISER,
PILISERO(?), PYLISER, PYLLISER, PYLLYSER, PYLISER en PYLYSERE.

Aangenend (6)
Aangenendt (37)
Aangenent (10)
Aengenant (1)
Aengenend (20)
Aengenendt (5)
Aengenent  (12)
Agenent (9)
Angeneind (20)
Angenend (11)
Angenendt (39)
Angenent (418)

Nooteboom (390,ZH)
Nootenboom (324,ZH)
Noteboom (549,ZH)
Notenboom (903,ZH/NB)
Neuteboom (897,Ov)
Neutenboom (3)
Notebomer (36,Gr)
Notenbomer (63, Gr)
Nottebaum (1)
Nottebohm (1)
Notteboom (1)
Nussbaum (40, Den Haag/Amsterdam)
Nussbaumer (1)
Nuszbaum (8, Amsterdam)
Nuszbaumer (3)

varianten zonder s:

Piper
Pieper
Peiper
Pijper
Pyper
Peijper
Peyper
Peiffer
Pfeiffer
Pijffer
Pfijffer
Pyffer
Pfyffer
Pijger
Peijger
Peiber
Pipper
Pipertz
le Pipere
le Pypere
le Pijpere
de Pijper
de Peijper
van der Pijpen
van der Pypen
van der Piepen
varianten met s:

Pipers
Piepers
Peipers
Pijpers
Pypers
Peijpers
Peypers
Pijepers
Peiffers
Pfeiffers
Pijffers
Pfijffers
Pyffers
Pfyffers
Pijgers
Peijgers
Peibers
Pippers
Peijpersz
de Pijpers
de Peijpers

http://www.gensdvf.nl/varianten.html 

Williamson
Williemson
Williamsen 
Williamsohn
Villiamson 
Wilhelmson
"""
 
def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite(SoundexNLTestCase),
        unittest.makeSuite(IdealWorldNLTestCase),
        ))

if __name__=='__main__':
    unittest.main(defaultTest='test_suite')
    
