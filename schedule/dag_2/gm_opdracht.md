## Opdracht voor ontdubbelen (disambiguatie) van namen

+ [Introductie](#intro)
    + [Data](#data)
+ [Opdracht](#opdracht)
+ [Resultaten](#resultaten)

<a name="intro"></a>
## Introductie

Met deze opdracht krijg je inzicht in de mogelijkheden en moeilijkheden van een bestaande '_back-of-book_'-index bij digitaal toegankelijk maken van een corpus.
Daarvoor moet je data opschonen, ontdubbelen en verrijken.

**Vraag:** _Op welke manier kunnen de Generale Missiven van de VOC inhoudelijk toegankelijk gemaakt worden._

We hebben de beschikking over de registers van de gedrukte delen missiven. Voor de opdracht hebben we er een paar geselecteerd. Zie de [toelichting bij de data](gm_toelichting.md).

<a name="data"></a>
### Dataset: Geselecteerde delen Generale missiven. Zie ook de [toelichting](gm_toelichting.md)

De [Generale Missiven data](https://surfdrive.surf.nl/files/index.php/s/OjzD8hZlVvDU12c) zijn als gezipt bestand te downloaden.


<a href="opdracht"></a>
### Opdracht:
_Bepaal aan de hand van de beschikbare registers of een samenhangende toegang tot het corpus van generale missiven mogelijk is en hoe dit dan globaal geconstrueerd zou kunnen worden_

+ Maak een opzet van een werkplan.

+ Bij welk register kun je het beste beginnen? Of maakt dat niet uit?

+ Welk register vind je het meeste beloven?

+ Hoe kun je termen disambiguëren?

+ Verzin manieren om verschillende soorten termen te groeperen/classificeren



## Uitwerking

**Stappen:**
+ Waar te beginnen. De registers van deel 13 komen uit een database, die van de andere delen zijn automatisch gegenereerd uit de ocr, met alle mogelijke fouten vandien. Het is het slimst deel 13 als uitgangspunt te nemen.

+ Bepalen van overlap. Er zijn verschillende typen registers. Welke zijn het meest veelbelovend? Wat kun je eigenlijk verwachten van een toegang.

+ Vergelijk indices met Open Refine. Intern zijn registers al grotendeels ontdubbeld; overweeg termen met subitems samen te voegen. Onderling zijn de termen niet ontdubbeld.

+ Het blijkt dat de overlap gering is bij alle termen. Hou het doel van registers in boek en digitaal uit elkaar. In een boek was het vrijwel onmogelijk een naam te vinden zonder toegang, digitaal is dat simpel. Categoriseren is een oplossing. Maar hoe? Pogingen - scheiden van Europese en niet-Europese namen (in de praktijk Nederlands en Maleis, maar fouten).

+ Kunnen we het aantal indextermen in het zakenregister terugbrengen? Het zakenregister tussen de twee laatste delen vertoont grotere overeenkomsten dan met de voorgaande, dat is waarschijnlijk veroorzaakt doordat de bewerker daar dezelfde was.
Zijn plaatsnamen tot regio’s te herleiden?

+ Probeer trefwoorden met co-occurrence met elkaar in verband te brengen, door paginanummers aan elkaar te verbinden. Hiervoor kun je het beste Open Refine gebruiken. Leg een relatie tussen bijvoorbeeld personen en geselecteerde zakentrefwoorden.


<a href="resultaten"></a>
### Resultaten

+ Inzicht in de powerlaw verdeling van personen, plaatsen etc. en de consequenties voor ontsluiting en mogelijkheden tot koppelen van data
+ Het belang van context voor disambiguëren en de moeilijkheden daarvan. Bij registers al moeilijk - hoe gaat dat met NER?
+ Misschien moeten we ook de beperkingen van Open Refine en het belang van programmeervaardigheden laten zien in het manipuleren van data
