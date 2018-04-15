Originele aanleiding: In “Er was iets met die schilders in de Gouden Eeuw” (NRC, 24-11-2011, pp.14-15) werden demografen Frans van Poppel, Dirk van de Kaa en Govert Bijwaard die op basis van de database van het Rijksbureau voor Kunsthistorische Documentatie stelden dat in de zeventiende eeuw schilders langer leefden dan aristocraten. De vraag: is dat zo?
Hoe was het verloop van de levensduur in de loop der eeuwen?

Input is een dataset van personen uit het Biografisch Portaal. DIe is niet helemaal up-to-date, maar dat is voor deze opdracht verder niet bezwaarlijk.


Probleem Opschonen en verwerken van tabellarische data tot overzicht
Beginnen met de bioport interface zelf?
Stap1: de data zijn in csv formaat, en niet helemaal in bruikbare vorm
Opschonen: omzetten numeriek getallen naar echter getallen; datatimegetallen naar data;
Verwijderen nulls (dat is optisch, maar ok); controle op importfouten
Tools: mogelijk met Open Refine, Spreadsheet, programmatisch (bv Python Pandas). Let Op: er zit een encoding probleem in ivm locale gekte van MySql. Open Refine importeert de dataset goed, andere programmatuur kan er niet goed mee overweg zonder nadere ingrepen.
Stap 2: Selecteer data voor verdere bewerking
Voor lang niet alle personen zijn de gegevens benodigde gegevens compleet.
Welke datum kiezen we
Wat te doen met overbodige gegevens (namen, extra datums,  geboorte-/sterfplaats)?
Tools: idem als boven.
Geboortejaar en sterfjaar zijn het meest compleet, dus geven meeste resultaten. Dat is wel minder precies, maar in dit geval te verkiezen boven minder data (die ook niet altijd exact zijn). We gaan ervan uit dat de afwijkingen in leeftijdsberekeningen elkaar uitmiddelen. Alleen personen met zowel geboorte- als sterfjaar doen mee. Neem ook degenen mee zonder sterfdatum , maar
Stap 3: Maak overzicht van de data
Daarvoor sterfjaar en geboortejaar van elkaar aftrekken. Voeg extra kolom toe, zo te zien kan dat niet zomaar in Google Refine, gebruikt dan een spreadsheet
Maak draaitabellen van de spreadsheet. Dit gaat niet automatisch helemaal goed, want de draaitabellen:
groeperen naar ranges jaren, bijvoorbeeld per eeuw. Bedenk ook dat een tabel op een pagina moet passen!
Houd daarbij ook rekening met de evidente fouten die in het bestand zitten (weggooien !), want die vertekenen de uitkomsten. Er zijn waarschijnlijk nog meer fouten, door verkeerde invoer, bijvoorbeeld. Die zijn niet uit te filteren, maar ga ervan uit dat ze uitmiddelen. Voor de periode vóór 1500 wordt het aantal personen wel erg klein, overwegen weg te laten
Het overzicht kan worden gemaakt voor het totaal aan data, maar voor een fijnmaziger verdeling kan ook gebruik worden gemaakt van de onderverdeling naar categorieën. Dit behoeft wel enige massage (samenvoegen categorieën, ordenen, weglaten als er te weinig data zijn?)
Stap 4: analyseer de data:
welke conclusies kunnen we trekken tav van de vraag?
Welke kanttekeningen zijn er te zetten bij de conclusies?
Zijn er behalve de oorspronkelijke vraag nog andere conclusies?
Hoe representatief zijn deze data?

Extra mogelijkheden: andere analyses die met de dataset zijn te maken. Voorbeelden:
Van wie zijn de exacte geboorte/sterfdata bekend? Wat kun je met onbekende geboorte/sterfdata??
Vergelijk geboorte en sterfteplaatsen in de tijd en per groep. Laat ze op een kaart zien. Bijvoorbeeld met Palladio
Uitbreiden van de dataset met de dominees uit Mining Ministers (https://github.com/cltl/Mining-Ministers ). Dit is vooral nuttig er meer computationeel onderlegden tussen zitten, want die kunnen dan alles online ophalen, uitpakken spreadsheet maken en vergelijken. Nog een idee: in plaats van de Geonames lokaties de data van histopo gebruiken (http://api.histopo.nl/docs/for-api-users/search.html) (of van Huygens als die beschikbaar komen)
