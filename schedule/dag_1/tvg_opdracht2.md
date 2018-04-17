# TvG Opdracht deel 2: Frequentielijsten, namen en temporele expressies

+ [Overzicht met woordfrequentielijsten](#grep-words-frequencies)
    + [Transliteratie: eenvoudige datatransformaties voor normalisatie](#grep-tr)
    + [Een stopwoordenlijst maken](#grep-stopwords)
    + [Een woordfrequentielijst maken](#grep-frequency-lists)
    + [Bigrammen: combinaties van twee woorden](#grep-bigrams)
+ [Overicht van namen, datums en periodes](#grep-names-dates)
    + [Zoeken met karaktersets](#grep-character-sets)
    + [Overzicht van datums, jaartallen en periodes](#grep-dates)
    + [Overzicht van namen](#grep-names)
    + [Zoeken naar auteursnamen](#grep-author-names)
+ [Term snowballing en het modelleren van topics](#grep-topics)
    + [Snowballing voor nieuwe termen uit Woordcontexten](#grep-snowballing)
    + [Snowballing met bigrammen](#grep-snowballing-bigrams)

Eerdere delen TvG opdracht:

+ [Deel 1 van de TvG opdracht](../dag_1/tvg_opdracht1.md) (dag 1)
+ [Deel 3 van de TvG opdracht](../dag_2/tvg_opdracht3.md) (dag 2)

**Open een document voor het bijhouden van data interacties om tot data scope te komen en overwegingen daarbij.** Gebruik bij voorkeur een nieuw Google Doc in de [workshop drive folder](https://drive.google.com/drive/folders/1R8Rex2v0YwfWhW8omEp0esqBkdX_Ymhr) op Google Drive, zodat alle aantekeningen bij elkaar staan zodat we die aan het eind de dag makkelijk kunnen vergelijken. 

<a name="grep-words-frequencies"></a>
## Overzicht met woordfrequentielijsten

In deze opdracht leer je hoe je een woordenlijst met frequenties kan maken van tekstuele data, hoe je een stopwoordenlijst kunt maken en die kunt gebruiken om woordenlijsten te filteren. Daarnaast leer je ook om lijsten van woord-bigrammen (woordparen) en woord-trigrammen (sets van drie woorden) te maken.

<a name="grep-tr"></a>
### Transliteratie: eenvoudige datatransformaties voor normalisatie

Het commando `cat` concateneert de inhoud van meerdere bestanden en toont ze op het scherm. Dit is handig om alle tekst van een editie achter elkaar te zien of door te sturen naar een volgend commando. Begin eerst met de inhoud van bijv. pagina's 125 van de 111de editie:

```bash
cat tvg_111/tvg_111_page_125.txt
```

De output kun je ook doorsturen naar het `tr` commando (voor *translate characters*) waarmee je algemene patronen kunt definieren om individuele karakters te veranderen of verwijderen. Bijvoorbeeld alle spaties vervangen door een *newline character* (`\n`) waardoor alle woorden op afzonderlijke regels komen:

```bash
cat tvg_111/tvg_111_page_125.txt | tr ' ' '\n'
```

Dit kun je sorteren en tellen:

```bash
cat tvg_111/tvg_111_page_125.txt | tr ' ' '\n' | sort | uniq -c
```

Je ziet dat er allerlei punctuatie aan woorden vastgeplakt zit. Die kun je met `tr` verwijderen. De set `[:punct:]` staat voor alle (?) punctuatiesymbolen. Met de parameter `-d` kun je aangeven dat die symbolen verwijderd moeten worden:

```bash
cat tvg_111/tvg_111_page_125.txt | tr '[:punct:]' ' ' | tr ' ' '\n' | sort | uniq -c
```

Als je door de lijst met woorden scrolt zie je dat woorden die beginnen met hoofdletters geplaatst worden voor de woorden die beginnen met kleine letters. Sommige van die woorden zijn namen, andere zijn de eerste woorden van zinnen. Om te zorgen dat bijv. 'de' en 'De' als hetzelfde woord worden gezien, kun je `tr` ook gebruiken om van alle hoofdletters kleine letters te maken.

De set hoofdletters kun je aangeven met `[:upper:]`, de kleine met `[:lower:]`. Door dit `tr` commando uit te voeren alvorens het sorteren en tellen, worden variaties in hoofdlettergebruik samengevoegd tot een variant met uitsluitend kleine letters:

```bash
cat tvg_111/tvg_111_page_125.txt | tr '[:punct:]' ' ' | tr '[:upper:]' '[:lower:]' | tr ' ' '\n' | sort | uniq -c
```

Vervolgens kun je uitzoomen naar de hele 111de editie, door `tvg_111_page_125.txt` te vervangen door `*.txt` (dit kan best even duren):

```bash
cat tvg_111/*.txt | tr '[:punct:]' ' ' | tr '[:upper:]' '[:lower:]' | tr ' ' '\n' | sort | uniq -c
```

**Datakritiek**: Je ziet nu duidelijk dat het TvG corpus bijzondere karakters bevat zoals `ĳ` en `ﬂ`. Dit is een eigenaardigheid van het OCR proces, waarbij *ij* soms als `ij` wordt herkend en soms als `ĳ`. Deze variaties zou je kunnen kunnen normaliseren door o.a. `ĳ` te vervangen door `ij` en `ﬂ` door `fl`. In deze opdracht wordt daar verder geen aandacht aan besteed, maar het is goed om dit in het achterhoofd te houden bij het interpreteren van verdere analyses.

<a name="grep-stopwords"></a>
### Een stopwoordenlijst maken

De volgende stap is het maken van een stopwoordenlijst. Er bestaan standaardlijsten (e.g. [snowball](http://snowball.tartarus.org/algorithms/dutch/stop.txt), [stopwords-iso](https://github.com/stopwords-iso/stopwords-nl)), maar stopwoorden zijn eigenlijk afhankelijk van de data (e.g. het domein) en de onderzoeksvraag. Je kunt je bijvoorbeeld afvragen of in het Tijdschrift voor Geschiedenis, het woord *geschiedenis* een stopwoord is of niet. Het is een van de meest frequente woorden, en helpt weinig bij het verkrijgen van een overzicht van de data, maar voor sommige vragen en zeker in de context van langere frases zal het een waardevol woord zijn. 

Sorteer eerst de lijst uit de vorige stap op frequentie:

```bash
cat tvg_111/*.txt | tr '[:punct:]' ' ' | tr '[:upper:]' '[:lower:]' | tr ' ' '\n' | sort | uniq -c | sort -g
```

Vervolgens kun je met `awk` de tweede kolom (`$2`) tonen voor regels waar de waarde van de eerste kolom (`$1`) groter is dan bijv. 100 (`awk` is bijzonder krachting maar ook complex en vergt veel uitleg die hier over wordt geslagen. Voor veel meer info zie de [Grymoire Awk tutorial](http://www.grymoire.com/Unix/Awk.html)). De output van dit geheel kun je opslaan in een bestand `stopwoorden_tvg.txt` die je eventueel handigmatig kunt bijwerken:

```bash
cat tvg_111/*.txt | tr '[:punct:]' ' ' | tr '[:upper:]' '[:lower:]' | tr ' ' '\n' | sort | uniq -c | sort -g | awk '{if ($1 > 100) print $2}' > stopwoorden_tvg.txt
```

Deze lijst bevat nu woorden die je wellicht niet als stopwoorden wilt beschouwen, dus verwijder met een text editor de regels uit het bestand voor niet-stopwoorden. Uiteraard kun je ook woorden toevoegen. Zorg ervoor dat elk woord op een aparte regel staat, zonder spaties.


Je kunt ook makkelijk bijhouden welke termen je uit de stopwoordenlijst verwijderd hebt in de vorige stap, om expliciet te maken wat je niet als stopwoord beschouwd. Met de `grep` parameter `-v` geef je aan dat alleen regels wilt zien die **niet** matchen met een opgegeven patroon, en met `-f` kun je een bestandsnaam opgeven van patronen waar je mee wilt matchen. Zo kun je makkelijk alle stopwoorden verwijderen uit een lijst. Door opnieuw een lijst van meest frequente woorden te maken en daarna de stopwoorden te laten verwijderen, krijg je te zien welke woorden je uit de stopwoordenlijst verwijderd hebt. Dit kun je weer in een bestand opslaan voor later gebruik:

```bash
cat tvg_111/*.txt | tr '[:punct:]' ' ' | tr '[:upper:]' '[:lower:]' | tr ' ' '\n' | sort | uniq -c | sort -g | awk '{if ($1 > 100) print $2}' | grep -f -v -w stopwoorden_tvg.txt > tvg-frequente-niet-stopwoorden.txt
```

Om duidelijk te zien dat stopwoordenlijsten afhankelijk zijn van de eigenschappen van je bronmateriaal, kun je een frequentielijst maken van een veel oudere editie en die filteren met de zojuist gemaakte stopwoordenlijst:

```bash
cat tvg_11/*.txt | tr '[:punct:]' ' ' | tr '[:upper:]' '[:lower:]' | tr ' ' '\n' | sort | uniq -c | sort -g | awk '{if ($1 > 100) print $2}' | grep -f -v -w stopwoorden_tvg.txt
```

Je ziet nu dat de meest frequente woorden ook weer veel stopwoorden bevatten, waaronder historische varianten van moderne stopwoorden. Een stopwoordenlijst voor modern Nederlands is dus maar beperkt effectief voor ouder materiaal. Uiteraard kun je je stopwoordenlijst uitbreiden met deze historische varianten en andere typische stopwoorden van het oudere materiaal om een algemene stopwoordenlijst voor het TvG corpus te maken (of een lijst die specifiek voor je onderzoeksfocus).


<a name="grep-frequency-lists"></a>
### Een woordfrequentielijst maken

Nu kun je de woordenlijst filteren op stopwoorden met `grep` en de parameters `-w` (match alleen hele woorden), `-f` (grep alle patronen uit een bestand, waarbij elke regel als een patroon wordt beschouwd) en `-v` (selecteer alleen regels als ze niet matchen):

```bash
cat tvg_111/*.txt | tr '[:punct:]' ' ' | tr '[:upper:]' '[:lower:]' | tr ' ' '\n' | grep -v -w -f stopwoorden_tvg.txt | sort | uniq -c | sort -g
```

<a name="grep-bigrams"></a>
### Bigrammen: combinaties van twee woorden

Het commando `awk` kan gebruikt worden om voor een woordenlijst de vorige regel te combineren met de huidige regel van de output, waarmee je woord-bigrammen kunt creeeren. Als je die stap doet voor het filteren van stopwoorden, krijg je woord-bigrammen waarbij beide woorden geen stopwoorden zijn:

```bash
cat tvg_111/*.txt | tr '[:punct:]' ' ' | tr '[:upper:]' '[:lower:]' | tr ' ' '\n' | awk 'prev!="" {print prev,$0} {prev=$0}' | grep -v -w -f stopwoorden_tvg.txt | sort | uniq -c | sort -g
```



<a name="grep-names-dates"></a>
## Overzicht van datums, jaartallen, periodes en namen

<a name="grep-chararter-sets"></a>
### Zoeken met karaktersets

Je kunt ook sets van karakters opgeven als zoekpatroon. Bijvoorbeeld, `[a-z]` geeft aan *alle karakters van a tot en met z*, of `[a-p]` voor *alle karakters van a tot en met p*. Dit is hoofdlettergevoelig (tenzij je met `grep` de optie `-i` gebruikt voor *case-insensitive*), dus `[a-z]` is anders dan `[A-Z]`. Cijfers kunnen ook in sets gedefinieerd worden: `[0-9]` voor *0 tot en met 9* of `[2-4]` voor *2 tot en met 4*. Het is ook mogelijk om sets te maken met combinaties van kleine en hoofdletters en cijfers, e.g. `[a-gD-J3-7]` of `D-J3-7a-g]` (de volgorde van de subsets maakt niet uit).

zoeken naar losse hoofdletters:

```bash
grep -E -h --color -w "[A-Z]" tvg_111/*.txt
```

Zoeken naar woorden bestaande uit 2 of 3 hoofdletters:

```bash
grep -E -h --color -w "[A-Z]{2,3}" tvg_111/*.txt
```

Zoeken naar woorden bestaande 3 of meer hoofdletters:

```bash
grep -E -h --color -w "[A-Z]{3,}" tvg_111/*.txt
```

Zoeken naar woorden bestaande 3 of meer hoofdletters in de set *A tot en met G*:

```bash
grep -E -h --color -w "[A-G]{3,}" tvg_111/*.txt
```

Zoeken naar woorden bestaande uit 2 of 3 hoofdletters afgewisseld met punten:

```bash
grep -E -h --color -w "([A-Z]\.){2,3}" tvg_111/*.txt
```

Dit zouden afkortingen kunnen zijn, maar lijken ook wel de voorletters van namen. Hier komen we zo op terug. Eerst nog wat andere voorbeelden van karaktersets proberen.

Zoeken naar combinatiesets van hoofdletters en getallen:

```bash
grep -E -h --color -w "[A-Z0-9]{3,}" tvg_111/*.txt
```

<a name="grep-dates"></a>
### Overzicht van datums, jaartallen en periodes

Zoeken naar getallen met tenminste 3 cijfers:

```bash
grep -E -h --color -w "[0-9]{3,}" tvg_111/*.txt
```

Zoeken naar jaartallen:

```bash
grep -E -h --color -w "1[0-9]{3}" tvg_111/*.txt
```

Er zitten ook OCR fouten in de data waardoor jaartallen soms beginnen met een `l` i.p.v. een `1`. Je kunt het patroon uitbreiden om ook die voorkomens te vinden:

```bash
grep -E -h --color -w "[1l][0-9]{3}" tvg_111/*.txt
```

Om te zien hoe vaak dit gebeurt (en of het dus de moeite waard is hier specifiek normalisaties en uitzondingerscategorieen voor te verzinnen), kun je heel makkelijk tellingen maken en vergelijken.

Eerste tellen met zowel `1` als `l`:

```bash
grep -E -h --color -w "[1l][0-9]{3}" tvg_111/*.txt | wc -l
```

Daarna met alleen `1`:

```bash
grep -E -h --color -w "[1][0-9]{3}" tvg_111/*.txt | wc -l
```

Daarna voor controle met alleen `l`:

```bash
grep -E -h --color -w "[l][0-9]{3}" tvg_111/*.txt | wc -l
```

Om te controlleren dat de voorkomens `l[0-9]{3}` wel degelijk jaaraanduidingen zijn kun je `| wc -l` weglaten om de matches te zien in hun context:

```bash
grep -E -h --color -w "[l][0-9]{3}" tvg_111/*.txt
```

Het zijn dus wel degelijk voornamelijk jaaraanduidingen.

Het patroon voor jaartallen kun je combineren met patronen voor maanden en dagen om naar voorkomens van specifieke datums te zoeken:

```bash
grep -E -h --color -w "(januari|februarui|maart|april|mei|juni|juli|augustus|september|oktober|november|december) [1l][0-9]{3}" tvg_111/*.txt
```

Je ziet dat een resultaten refereren naar een maand, maar sommige naar specifieke dag. Je kunt het patroon uitbreiden zodat die specifieke dagen matchen:

```bash
grep -E -h --color -w "[0-9]{1,2} (januari|februarui|maart|april|mei|juni|juli|augustus|september|oktober|november|december) [1l][0-9]{3}" tvg_111/*.txt
```

Als je dit herhaalt op een oudere editie merk je iets vreemds:

```bash
grep -E -h --color -w "[0-9]{1,2} (januari|februarui|maart|april|mei|juni|juli|augustus|september|oktober|november|december) [1l][0-9]{3}" tvg_04/*.txt
```

Er lijken nul resultaten te zijn. Worden er geen datums genoemd in oudere teksten of is er iets anders aan de hand? Als je *case-insensitive* zoekt wordt duidelijk waarom je in eerste instantie niets vond:

```bash
grep -E -i -h --color -w "[0-9]{1,2} (januari|februarui|maart|april|mei|juni|juli|augustus|september|oktober|november|december) [1l][0-9]{3}" tvg_04/*.txt
```


Bedenk patronen om te zoeken naar:

- Andere datumaanduidingen
- Eeuwen en decennia
- Jaaraanduidingen in Romeinse cijfers
- periodes (e.g. 1914-1918)

### Jaartallen groeperen per decennium of eeuw

Het kan ook handig zijn voor het structureren van temporele informatie om bijvoorbeeld jaartallen te groeperen per decennium of eeuw. Zo kun je makkelijk pagina's of edities vinden die over specifieke decennia of eeuwen spreken, of hoe een specifiek decennium of specifieke eeuw door de hele TvG genoemd wordt.

Dit kun je doen doet het matchende patroon te *transformeren* m.b.v. bijvoorbeeld het commando `sed` (voor *stream editor*). Een standaard reguliere expressie is alleen voor het matchen en heeft in `sed` de voor `'m/patroon/gi'` waarbij de initiele `m` staat voor `match` en de parameters aan het eind gebruikt kunnen worden om aan te geven of het patroon *case-insensitive* (`i`) of *case-sensitive* (`I`) moet matchen (zonder `i` of `I` is de standaard matching *case-sensitive*), en of het alleen om de eerste in de regel gaat, of dat alle voorkomens in de regel gematched moeten worden (`g` voor *global*). 

Een alternatief patroon is `'s/origineel-patroon/nieuw-patroon/'` waarbij de `s` staat voor *substitutie* en er voor zorgt dat het originele patroon wordt vervangen door het nieuw patroon. Zo kun je bijvoorbeeld jaartallen laten vervangen door een decennium door het laatste getal te vervangen door een nul. 
Je kunt de eerste drie getallen in parentheses zetten om er naar terug te kunnen refereren in het vervangende patroon met `\1`:

```bash
grep -E --colour -o -w "[1l][0-9]{3}" tvg_04/*.txt | sed -E 's/([1l][0-9]{2})[0-9]/\10/g'
```

Als je meerdere groepen in parentheses definieert kun je er naar terugrefereren met oplopende getallen. E.g. de eerste groep met `\1`, de tweede met `\2` etc. Zo kun je zowel het originele jaar als het bijbehorende decennium laten tonen:

```bash
grep -E --colour -o -w "[1l][0-9]{3}" tvg_04/*.txt | sed -E 's/([1l][0-9]{2})([0-9])/\1\2 \10/g'
```

Ook de jaartallen met een `l` i.p.v. een `1` kun je transformeren:

```bash
grep -E --colour -o -w "[1l][0-9]{3}" tvg_04/*.txt | sed -E 's/([1l])([0-9]{2})([0-9])/\1\2\3 1\2\3 1\20/g'
```

Zo zie je de editie, het paginanummer, het jaargetal zoals het in de editie voorkomt, het opgeschoonde jaar (altijd met `1` i.p.v. met `l`) en het bijbehorende decennium. Met vergelijkbare stappen kun je nu ook de eeuw erbij plaatsen. Zo kun je dus ingangen creeeren via jaartallen, decennia en eeuwen om bijbehorende pagina's in edities te vinden, ook al bevatten die pagina's die aanduidingen niet letterlijk.

**vraag**: met welke data scope activiteit zou je deze stap associeren?

Uiteraard kun je deze output weer naar een bestand schrijven voor latere analyse of om aan een database toe te voegen voor makkelijk bevragen van de data.

<a name="grep-names"></a>
### Overzicht van namen

Zoeken naar woorden die beginnen met een hoofdletter:

```bash
grep -E -h --color -w "[A-Z]\w+" tvg_111/*.txt
```

Het resultaat levert allerlei namen op, maar ook de eerste woorden van zinnen, die immers ook met een hoofdletter beginnen.

Er zijn ook dubbele namen met bijvoorbeeld een verbindingsteken. Je kunt dit ook opnemen in de reguliere expressie en zoeken naar woorden die beginnen met een hoofdletter en een combinatie van letters en verbindingstekens mogen bevatten:

```bash
grep -E -h --color -w "[A-Z](\w|-)+" tvg_111/*.txt
```

Dit levert ook samengestelde namen op, zoals Noord-Nederland. Je kunt `--color` vervangen door `-o` om alleen de matchende delen te tonen, zodat je een wat overzichtelijkere lijst krijgt:

```bash
grep -E -h -o -w "[A-Z](\w|-)+" tvg_111/*.txt
```

Met sorteren en tellen krijg je beter zicht op de meest gevonden patronen:

```bash
grep -E -h --color -o -w "[A-Z](\w|-)+" tvg_111/*.txt | sort | uniq -c | sort -g
```

Er zitten allerlei namen bij, maar ook voor stopwoorden als eerste woord in de zin. Veel namen zijn het eerste woorden van een meerwoordsnaam. Breidt het patroon eerst uit om twee-woordsnamen te vinden:

```bash
grep -E -h --color -o -w "[A-Z](\w|-)+ [A-Z](\w|-)+" tvg_111/*.txt | sort | uniq -c | sort -g
```

Maar er zijn ook namen met meer dan twee woorden, dus het eerste deel kan zich herhalen (dit patroon als makkelijk verkeerd getypt. Let goed op hoe het verschilt van het bovenstaande: het groepeert een hoofdletterset `[A-Z]`, een sequentie van *letter* en *verbindingsteken* karakters `(\w|-)+`, een spatie, en geeft vervolgens aan dat die groep kan zich herhalen `([A-Z](\w|-)+ )+`):

```bash
grep -E -h --color -o -w "([A-Z](\w|-)+ )+[A-Z](\w|-)+" tvg_111/*.txt | sort | uniq -c | sort -g
```

Er worden sommige namen samengevoegd, zoals *Konstantinopel F. Van Tricht*. Een ander probleem is dat nu namen van een enkel woord nu niet gevonden worden. Dat laatste is makkelijk aan de te passen door het herhalingsteken `+` van de buitenste groepering te vervangen door `*`:

```bash
grep -E -h --color -o -w "([A-Z](\w|-)+ )*[A-Z](\w|-)+" tvg_111/*.txt | sort | uniq -c | sort -g
```

Dit levert veel stopwoorden op. Je kunt hier allerlei trucs op verzinnen. Direct filteren op stopwoorden heeft het nadelige effect dat ook namen als *De Ronde Tafel Conferentie* weggefilterd wordt. Hier is een ingewikkelder set stappen nodig, waarvoor het al snel makkelijker wordt om een andere toolset te gebruiken, e.g. Python en speciale modules voor tekst-analyse. Een veelgebruikte optie is een Named Entity Recognition tool te gebruiken, al zal die waarschijnlijk getraind moeten worden op deze specifieke dataset, vanwege alle eigenaardigheden ervan (grote periode met spellingsverschuivingen, OCR fouten, domeinspecifieke conventies, etc.). 

<a name="grep-author-names"></a>
### Zoeken naar auteursnamen

Auteursnamen worden vrijwel uitsluitend uitgedrukt met een combinatie van voorletters en achternaam. Je kunt dus zoeken naar een hoofdletter gevolgd door een punt, een spatie en dan een woord beginnend met een hoofdletter:

```bash
grep -E -h -o -w "[A-Z]\. [A-Z](\w|-)+" tvg_111/*.txt
```

Dit levert een lijst van persoonsnamen op. Waarschijnlijk zijn dit veelal auteurs van de verschillende artikelen, mededelingen en besproken boeken.

Soms word een voornaam afgekort tot twee letters, zoals *Th*. Het volgende patroon is voor zowel voornamen afgekort met een enkele hoofdletter als voor voornamen afgekort met een hoofdletter en een kleine letter:

```bash
grep -E -h -o -w "[A-Z][a-z]?\. [A-Z](\w|-)+" tvg_111/*.txt
```

Deze namen kun je sorteren en tellen met een combinatie van `sort` en `uniq`:

```bash
grep -E -h -o -w "[A-Z][a-z]?\. [A-Z](\w|-)+" tvg_111/*.txt | sort | uniq -c | sort
```

We zien nu "F. Van" als meest frequente naam. Dat is waarschijnlijk een incomplete naam. 

```bash
grep -E -h -o -w "[A-Z][a-z]?\.( [A-Z](\w|-)+)+" tvg_111/*.txt | sort | uniq -c | sort
```

Bovendien zijn er waarschijnlijk ook veel namen waarbij "van" met kleine letters is geschreven. Andere tussenwoorden die veel voorkomen zijn "de" "der" "den":

```bash
grep -E -h -o -w "[A-Z][a-z]?\.( van| de| der| den)*( [A-Z](\w|-)+)+" tvg_111/*.txt | sort | uniq -c | sort
```

Waarschijnlijk zijn er ook namen met meerdere voorletters:

```bash
grep -E -h -o -w "([A-Z][a-z]?\.)+( van| de| der| den)*( [A-Z](\w|-)+)+" tvg_111/*.txt | sort | uniq -c | sort
```

Als we willen zijn op welke pagina's die namen voorkomen, kunnen we de optie "-h" weghalen, zodat de bestandsnamen geprint worden:

```bash
grep -E -o -w "([A-Z][a-z]?\.)+( van| de| der| den)*( [A-Z](\w|-)+)+" tvg_111/*.txt
```

### Zoekresultaten opslaan in een bestand

Resultaten schrijven naar een bestand:

```bash
grep -E -o -w "([A-Z][a-z]?\.)+( van| de| der| den)*( [A-Z](\w|-)+)+" tvg_111/*.txt > persoonsnamen-tvg_111.txt
```

Je kunt met `sed` ook de bestandsnaam nog veranderen zodat je een makkelijker leesbaar *comma-separated-value* bestand krijgt dat je met Excel, Google Spreadsheet of Open Refine kunt openen:

```bash
grep -E -o -w "([A-Z][a-z]?\.)+( van| de| der| den)*( [A-Z](\w|-)+)+" tvg_11[0-9]/*.txt | sed -E 's/.txt:/,/' | sed -E 's/tvg_[0-9]+\///' | sed -E 's/_page/,page/' > tvg_persoonsnamen.txt
```

<a name="grep-topics"></a>
## Term snowballing en het modelleren van topics

Om grip te krijgen op onderwerpen rondom een of meer specifieke termen (e.g. `migratie`, of `Gouden Eeuw`) is het handig om eerst te zien welke andere woorden en woord-bigrammen (woordcombinaties van twee woorden) daarbij in de buurt voorkomen. Onderstaande oefeningen laten zien hoe je met een zogenaamde *snowballing* strategie kunt zoeken naar gerelateerde termen waarmee je data-gedreven het onderwerp kunt modelleren.

De term *snowballing* is een bestaande term voor een zoekstrategie waarbij je beginnend met een enkele of een paar termen gaat zoeken naar materialen en door close reading gerelateerde termen vindt, waarme je vervolgens opnieuw kunt zoeken en nog meer termen te vinden, totdat je geen nieuwe gerelateerde termen meer vindt. 

<a name="grep-snowballing"></a>
### Snowballing voor nieuwe termen uit Woordcontexten

Met de volgende keten van commando's kun je de woorden in de zinnen rondom een zoekpatroon analyseren:

```bash
grep -r -E -h -i -w "\w+migra[nt]\w+" tvg_*/ | tr '[:punct:]' ' ' | tr '[:upper:]' '[:lower:]' | tr ' ' '\n' | grep -v -w -f tvg_stopwoorden.txt | grep -v -E -w "\w{,2}" | sort | uniq -c | sort -g
```

Wat staat hier eigenlijk? Een ontleding van deze keten:

- `grep -r -E -h -i -w`: grep recursief door een of meer directories (`-r`), interpreteer het zoekpatroon als reguliere expressie (`-E`), laat de namen van matchende bestanden weg (`-h`), match hoofdletter-*ongevoelig*, en match alleen als het zoekpatroon begint en eindigt op een woordgrens (`-w`). Deze laatste optie is in dit geval overbodig omdat zowel aan het begin als eind van het zoekpatroon `\w+` staat waarmee zogenaamd *greedy* gematched, e.g. stop pas als je geen `\w` karakters meer tegenkomt rondom het patroon daartussen.
- `"\w*migra[nt]\w+"`: match nul of meer `\w` karakters die gevolgd worden door `migra`, gevolgd door `n` of `t`, gevolgd door een of meer `\w` karakters. dus woorden die de string `migran` of `migrat` bevatten.
- `tvg_*/`: begin de directory recursie met de directories `tvg_*/`, dus alle directories die beginnen met `tvg_`.
- `tr '[:punct:]' ' '`: vervang elk punctuatiesymbool met een spatie.
- `tr '[:upper:]' '[:lower:]'`: vervang hoofdletters door kleine letters
- `tr ' ' '\n'`: vervang spaties door *newlines*, i.e. zet alle symbolen na een spatie op een volgende regel.
- `grep -v -w -f tvg_stopwoorden.txt`: grep alle regels die niet als woord (`-w`) matchen met de patronen gespecificeerd in het bestand (`-f`) `tvg_stopwoorden.txt`
- `grep -v -E -w "\w{,2}"`: grep alle regels met woorden die langer zijn dan 2 karakters.
- `sort | uniq -c | sort -g`: sorteer de output alfabetisch, tel daarna het aantal voorkomens van elk unieke regel, en sorteer vervolgens nog eens numerisch op frequentie.

Je kunt ook nog bepalen hoeveel context je wilt gebruiken door bijvoorbeeld ook de voorafgaande en volgende zinnen mee te nemen in het eerste grep commando. Met `-A 2` geef je aan dat je de twee regels na (**A**fter) een matchende regel wilt zien. Met `-B 3` krijg je de drie regels voor (**B**efore) de matchende regel.

<a name="grep-snowballing-bigrams"></a>
### Snowballing met bigrammen

Je kunt de commando-keten ook aanpassen zodat er woord-bigrammen worden geteld. In de oefening [Bigrammen: combinaties van twee woorden](#grep-bigrams) kun je zien hoe je met `awk` het woord op de huidige regel kunt aanpassen door het woord op de vorige regel ervoor te plaatsen met `awk 'prev!="" {print prev,$0}{prev=$0}'`

```bash
grep -r -E -h -i -w "\w+migra[nt]\w+" tvg_*/ | tr '[:punct:]' ' ' | tr '[:upper:]' '[:lower:]' | tr ' ' '\n' | awk 'prev!="" {print prev,$0} {prev=$0}' | grep -v -w -f tvg_stopwoorden.txt | grep -v -E -w "\w{,2}" | sort | uniq -c | sort -g
```

### Topic modelling

Een populaire optie is [probabilistic topic modelling](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4122269/) waarmee je algoritmisch coherente woordensets ("groups of tightly co-occurring words", topics) laat ontdekken in de data. Dit is vergelijkbaar met het handmatig modelleren van topics a.d.h.v. woordensets, alleen is dit vrijwel puur data-gedreven, dus je hebt weinig controle over het proces en de uitkomst (dit is in principe een positief aspect maar kan ook tot onbevredigende, oninterpreteerbare resultaten leiden). De [Topic Modelling Tool](https://senderle.github.io/topic-modeling-tool/documentation/2017/01/06/quickstart.html) pagina geeft goede instructies die ook toepasbaar zijn op het TvG corpus. Dit is een vorm van *classificatie*, alhoewel de tool zelf onder de motorkap allerlei bewerkingen uitvoert die onder *selectie* en *normalisatie* vallen (en in zekere zin ook *linking*).

Als je hiermee uitgeoefend bent, kun je door naar [deel 3 van de TvG opdracht](../dag_2/tvg_opdracht3.md) (dag 2)

