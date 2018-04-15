# Opdracht 1: Greppen in TvG Data

+ [Introductie](#intro)
    + [Data downloaden](#data)
    + [Research focus: wat ga ik onderzoeken?](#focus)
+ [Grip met grep: zoeken in data met behulp van reguliere expressies](#grep)
    + [Command Line: interactie via commando's](#grep-command-line)
+ [Overzicht van varianten en contexten voor specifieke woorden en frases](#grep-words)
    + [Zoeken met woordensets](#grep-word-sets)
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

<a name="intro"></a>
## Introductie

Met deze opdracht ontwikkel je de volgende vaardigheden:

+ grip krijgen op heterogene data met grote variatie
+ identificeren en duiden van patronen
+ gestructureerd omgaan met ongestructureerde data

De TvG Dataset is groot en beperkt gestructureerd. Er liggen talloze inzichten verborgen in de 121 jaargangen, maar de bestaande structuur geeft weinig handvatten om die inzichten naar voren te halen. Hoe kun je van deze brondata een data scope creeeren die verschillende perspectieven op het TvG corpus biedt waarmee je op een transparante manier tot nieuwe inzichten komt?

TO DO

+ keuzes in modelleren
+ definieren data assen
+ bijhouden van data interacties om tot data scope te komen

<a name="data"></a>
### Data downloaden

+ Je kunt het [hele TvG corpus als een zip bestand](https://surfdrive.surf.nl/files/index.php/s/MqRVCbAYpQBeEjO) downloaden.
+ Waar staat mijn data?
+ Hoe kan ik met command line tools bij mijn data?
    + commando's worden uitgevoerd vanuit een working directory (folder)
    + je kunt je working directory veranderen ('cd' for change directory)
    + je kunt  aangeven waar een command line tool de data kan vinden t.o.v. je working directory

Download de [TvG dataset]. *Voor Windows gebruikers die Git Bash hebben geinstalleerd, sla de dataset op in eennieuwe directory in de directory waar Git Bash is geinstalleerd. Anders kun je vanuit de command line niet bij de data.*

<a name="focus"></a>
### Research focus: wat ga ik onderzoeken?

_Wat is mijn onderzoeksvraag of thema?_

Je kunt van te voren vaststellen wat je wilt onderzoeken, maar de ervaring leert dat je dit tijdens het onderzoeksproces nog regelmatig zal herzien. Initiele aannames en verwachtingen blijken vaak niet goed genoeg op het bestaande materiaal aan te sluiten, waardoor je een onderzoeksvraag wilt aanpassen of over wilt stappen naar een compleet andere vraag. 

<a name="focus-selection"></a>
#### Selectie

_Welke informatie uit TvG is daarbij relevant?_

_Welke jaargangen, pagina's zeggen iets over mijn onderzoeksvraag/thema?_

<a name="focus-modelling"></a>
#### Modelleren

_Hoe vertaal ik onderzoeksvragen en methoden naar data interacties?_

Dit is een cruciale vraag en vergt continue reflectie op het proces. Voortschreidend inzicht tijdens het proces van data bevragen, bewerken en analyseren leidt tot aanpassingen in eerdere stappen. 

_Hoe representeer ik relevante informatie in mijn brondata?_

Bij het vertalen van je onderzoeksvraag naar data interacties om die vraag te adresseren, moet je keuzes maken over wat voor soort informatie je uit de data wilt halen, hoe je dat kunt doen en wat de consequenties van je keuzes is:

- Wat zijn de informatie-eenheden die je uit de data wilt halen?
- Waar legt jouw keuze de focus op en wat verdwijnt daarbij mogelijk naar de achtergrond? Wat mis je mogelijk?
- Welke alternatieve keuzes had je kunnen maken, en hoe zou dat tot andere focus en achtergrond leiden?

<a name="grep"></a>
## Grip met grep: zoeken in data met behulp van reguliere expressies

`grep` is een UNIX command line tool waarmee je kunt zoeken in data-bestanden naar regels die *matchen* met een reguliere expressie (**G**lobally search a **r**egular **e**xpression and **p**rint).

Eerst wat uitleg over de *command line* en hoe je navigeert naar verschillende mappen of directories op je harde schijf en andere aangesloten opslagmedia.

Een handige [`grep` cheat sheet](http://www.ericagamet.com/wp-content/uploads/2016/04/Erica-Gamets-GREP-Cheat-Sheet.pdf).

**Let op: de oefeningen worden al heel snel heel complex. Dit is puur om te laten zien wat mogelijk is, en waarom dit nuttig kan zijn. De syntax is cryptisch en exotisch en vergt veel oefening om het eigen te maken. Als je het nuttig vindt kun je er dus meer tijd in steken en wordt de systematiek al snel duidelijk. Als je hier niet zelf mee aan de slag wil, is het in ieder geval nuttig om te zien hoe het werkt, wat er mogelijk is, en waar potentiele problemen in de data een rol spelen.**

<a name="grep-command-line"></a>
### Command line: interactie via commando's

De command line is een alternatieve manier om te interacteren met de computer. I.p.v. opdrachten geven met de muis, geef je via de command line opdrachten d.m.v. commando's. Alhoewel dit voor veel mensen wennen is aan ongebruikelijke notatie en de onverbiddelijke precisie die vereist is, heeft het ook een aantal voordelen:

+ complexe commando's: het is mogelijk om commando's samen te stellen zodat in 1 regel meerdere opdrachten worden gegeven die achter elkaar worden uitgevoerd.
+ herhaalbaarheid: uitgevoerde opdrachten worden bewaard waardoor je makkelijk eerdere commando's nog een keer kunt uitvoeren. Dit is vooral handig voor complexe commando's of wanneer je een opdracht wilt herhalen met een kleine wijziging.
+ automatisering: je kunt de commando's bewaren in een bestand, zodat je op een later tijdstip kunt zien wat je eerder gedaan hebt. Daarnaast kun je lijsten van commando's in een bestand ook weer achter elkaar laten uitvoeren door het bestand `executable` te maken.

Voor transparant werken met data is het belangrijk en waardevol om uitgevoerde opdrachten bij te houden en te kunnen delen (ook met jezelf op een later tijdstip).

*Belangrijke tip: met de &uparrow; en &downarrow; toetsen kun je eerder uitgevoerde commando's terughalen, zodat je makkelijk kunt herhalen en aanpassingen kunt doen.*

Om onderstaande oefeningen te doen is het handig te navigeren naar de directory waar je de TvG data hebt opgeslagen. **De directory-structuur is een zogenaamde boom structuur, met een enkele stam (root) en een of meer vertakingen. In UNIX omgevingen is `/` het symbool voor de *root* directory, `/home` is de *home* directory binnen de *root* directory. Directories binnen andere directories (sub-directories) zijn vertakingen binnen vertakingen. Zo is je persoonlijke directory die overkomt met je gebruikersnaam een subdirectory van `/home`. Je kunt o.a. navigeren tussen directories via de vertakingen.**

+ navigeren tussen directories:
    + `pwd` (print working directory): waar ben ik? Het `pwd` commando laat zien in welke directory je de commando's uitvoert. 
    + `cd` (change directory): verander mijn *working directory* (*wd*). Je kunt je *wd* wijzigen met `cd`. Met `cd ~` verander je de *wd* naar je zgn. *home directory*, ofwel je persoonlijke directory (`/home/<gebruikersnaam>`). Als je daarbinnen een directory `data` hebt staan, kun je van daaruit navigeren naar de `data` directory met `cd data`. Met `cd ..` ga je een niveau omhoog in de directory-structuur
    + `ls` list: wat zit er in deze directory (e.g. mijn *working directory*)?
+ relatieve paden
    + `ls tvg/`: wat zit er in de subdirectory `tvg`? (dit gaat er vanuit dat de huidige *working directory* een subdirectory `tvg` heeft. Als dat niet het geval is dan leidt dit commando tot een error `no such file or directory`).
    + `ls ../`: wat zit er in de directory boven mijn huidige *working directory*?


<a name="grep-words"></a>
## Overzicht maken van varianten en contexten voor specifieke woorden en frases

Navigeer naar de directory waar je de TvG data hebt opgeslagen. Controleer dat je op de juiste plek bent door `ls` te typen. Als je de directories `tvg_1` etc. ziet staan ben je in de juiste directory. Zo niet, type dan `pwd` en vergelijk je huidige *working directory* met waar de data staat. 

Op de juiste plek aangekomen, kun je nu `grep` uitvoeren om naar patronen in de data te zoeken. Als eerste oefening, zoek voorkomens van het woord *politiek* in alle bestanden van de 111de editie:

```bash
grep "politiek" tvg_111/*.txt
```

Je krijgt een lijst te zien van alle regels (lines) van de verschillende bestanden waarin de tekststring *politiek* voorkomt. Aan het begin van elke regel toont `grep` de naam van het bestand waarbinnen de regel gevonden is (een *match*). 

Dit is ietwat onoverzichtelijk. Je kunt `grep` opdracht geven om het deel van de regel dat *matched* met je patroon in kleur weer te geven, zodat je sneller ziet wat de *match* is. Dit kan met de parameter `--color` of `--colour`:

```bash
grep --color "politiek" tvg_111/*.txt
```

Je ziet nu dat `grep` ook regels vindt waarin *politiek* een onderdeel is van een woord, zoals *politieke* en *bouwpolitiek*. Je kunt de parameter `-w` gebruiken om aan te geven dat `grep` alleen moet matchen met hele woorden (e.g. alleen als *politiek* het hele woord is). *Opmerking: het is gebruikelijk om alle parameters direct achter het `grep` commando te plaatsen, zodat je makkelijk kunt zien welke parameters gebruikt zijn. In de opdrachten hier beneden zul je zien dat er veel verschillende parameters zijn, en je vaak wil je er meerdere combineren. Dan is het handig om ze te groeperen, aan het begin of aan het eind van het commando.*

```bash
grep --color -w "politiek" tvg_111/*.txt
```

Je vraagt je wellicht af hoe `grep` weet wat hele woorden zijn. Dat wordt duidelijk na een aantal opdrachten hier beneden.

Standaard maakt `grep` een onderscheid tussen hoofdletters en kleine letters. Als je wilt zoeken zonder hoofdlettergevoeligheid, kun je de `-i` parameter gebruiken:

```bash
grep --color -w -i "politiek" tvg_111/*.txt
```

Net als met `CTRL-F` kun je met `grep` ook naar frases van meerdere woorden zoeken:
```bash
grep --color -w -i "binnenlandse politiek" tvg_111/*.txt
```

Om reguliere expressies te gebruiken kun je de parameter `-E` toevoegen (voor *extended regular expression*). Hiermee interpreteert `grep` het opgegeven patroon als een reguliere expressie i.p.v. een letterlijke string. Eerst wordt het zoekpatroon uitgebreid naar alle woorden die beginnen met *politiek*, eventueel gevolgd worden door 1 of meer letters (aangegeven met `\w*`.) De `\w` staat voor alles wat alfanumerisch is (letters en cijfers), de `*` staat voor nul, een of meer keren herhaald:

```bash
grep -E --color -w -i "politiek\w*" tvg_111/*.txt
```

Dit is vergelijkbaar met zoeken a.d.h.v. een zgn. *wildcard*, e.g. *politiek*\*. Het voordeel van reguliere expressies is dat je meer controle hebt over wat er op de plaats van het *wildcard* mag staan. Als je de `*` vervangt door een `+`, matched `grep` alleen met woorden die *beginnen* met *politiek* en gevolgd worden door tenminste een maar mogelijk meer alfanumerische karakters:

```bash
grep -E --color -w -i "politiek\w+" tvg_111/*.txt
```

De kracht van reguliere expressies wordt hieronder steeds duidelijker gemaakt. Je kunt bijvoorbeeld ook preciezer aangeven hoeveel extra karakters er moeten volgen, met behulp van accolades. E.g `\w{2,15}` betekent minimaal 2 en maximaal 15 extra alfanumerische karakters:

```bash
grep -E --color -w -i "politiek\w{2,15}" tvg_111/*.txt
```

Je kunt ook alleen een minimum aangeven (e.g. `{2,}`) of alleen een maximum (e.g. `{,15}`). 

Wat met *wildcards* vaak niet mogelijk is, is ze plaatsen aan het begin van een woord. E.g. om te zoeken naar alle woorden die *eindigen* op *politiek* kun je de expressie `\w+` ervoor plaatsen:

```bash
grep -E --color -w -i "\w*politiek" tvg_111/*.txt
```

Hiermee zie je voorkomens van verschillende vormen van politiek. Uiteraard kun je ook zoeken naar alle woorden die *politiek* bevatten aan het begin, midden of einde van een woord:

```bash
grep -E --color -w -i "\w*politiek\w*" tvg_111/*.txt
```

Je kunt nog veel complexere patronen definieren met reguliere expressies. Verderop staan oefeningen voor het zoeken naar namen, jaartallen en datums. Een andere mogelijkheid is het zoeken naar bijv. woorden die voorafgaan aan een woord dat matched met *politiek*. Door `\w+ ` te plaatsen voor `\w*politiek\w*` krijg je nu ook het voorafgaande woord te zien:

```bash
grep -E --color -w -i "\w+ \w*politiek\w*" tvg_111/*.txt
```

Ook twee woorden vooraf is mogelijk:

```bash
grep -E --color -w -i "\w+ \w+ \w*politiek\w*" tvg_111/*.txt
```

Een generiekere manier is om meerdere herhalingen te definieren. Je kunt een subpatroon definieren door het te plaatsen binnen parentheses, e.g. `(\w+ )`. Voor dit subpatroon kun je aangeven of het bijvoorbeeld nul of een keer mag voorkomen (`(\w+ )?`), een of meer keer (`(\w+ )+`), nul, een of meer keer (`(\w+ )*`), precies vijf keer (`(\w+ ){5}`) of maximaal drie keer (`(\w+ ){,3}`):

```bash
grep -E --color -w -i "(\w+ ){,3}\w*politiek\w*" tvg_111/*.txt
```

<a name="grep-pipelines"></a>
### Ketens van commando's: pipelines, sorteren en tellen

Met flexibele patronen wordt de lijst matches al snel erg lang en gevarieerd. Om beter zicht te krijgen op de verschillende matchende patronen, kun je `grep` ook opdracht geven om niet de hele regels, maar alleen de matchende delen te tonen, met de parameter `-o`:

```bash
grep -E --color -o -w -i "\w*politiek\w*" tvg_111/*.txt
```

Voor exploratie van een grote dataset kan het handig zijn om de gevonden patronen te sorteren en tellen, zodat je een beeld krijgt welke patronen veel en welke weining voorkomen. Voordat je dat doet is het handig om de output van `grep` nog zo aan te passen dat de bestandsnamen niet meer getoond worden, zodat echt alleen de matchende patronen getoond worden. Daarna is sorteren en tellen simpel. Je kunt de bestandnamen laten verbergen met de `-h` parameter:

```bash
grep -E -h -o -w -i "\w*politiek\w*" tvg_111/*.txt
```

UNIX biedt een eenvouig maar zeer krachtig mechanisme om de output van het ene commando direct door te sturen als input voor het volgende commando, d.m.v. zogenaamde *pipes*. Als je het `|` symbool plaatst aan het eind van het `grep` commando, wordt de output van `grep`, e.g. alle matchende patronen, doorgestuurd naar een volgend commando. Dit wordt ook wel *redirection* genoemd. 

Je kunt bijvoorbeeld het `wc` (*word, line, character and bye count*) commando gebruiken om te tellen hoeveel matches er zijn:

```bash
grep -E -h -o -w -i "\w*politiek\w*" tvg_111/*.txt | wc -l
```

De `-l` parameter telt het aantal regels (lines). Met `-w` telt `wc` het aantal woorden, met `-m` het aantal karakers.

Het `sort` commando sorteert input en toont de gesorteerde output weer op het scherm. Standaard sorteert `sort` alfabetisch in oplopende volgorde, maar je kunt ook numerisch sorteren en in aflopende volgorde. Dit ga net als met `grep` a.d.h.v. parameters. Voor nu volstaat dat standaard sortering:

```bash
grep -E -h -o -w -i "\w*politiek\w*" tvg_111/*.txt | sort
```

De meeste matches zijn voor de woorden *politiek* en *politieke*. Om een lijst van de unieke patronen te zien, kun je de output van `sort` doorsturen naar het commando `uniq` die bij opeenvolgende regels met exact dezelfde inhoud alleen de eerste laat zien:

```bash
grep -E -h -o -w -i "\w*politiek\w*" tvg_111/*.txt | sort | uniq
```

Met wederom een parameter kun je `uniq` laten tellen hoe vaak elk patroon voorkomt, e.g. `-c` voor count:

```bash
grep -E -h -o -w -i "\w*politiek\w*" tvg_111/*.txt | sort | uniq -c
```

Deze lijst kun je ook weer sorteren:

```bash
grep -E -h -o -w -i "\w*politiek\w*" tvg_111/*.txt | sort | uniq -c | sort
```

Nog een handige vorm van *redirection* is de output schrijven naar een bestand, zodat het niet slechts tijdelijk op je scherm getoond wordt, maar blijvend wordt opgeslagen. Zeker als er veel output gegenereerd wordt is een bestand handig. *Redirection* naar een bestand doe je a.d.h.v. het `>` symbool. Aan het eind van de keten van commando's kun je `> bestandsnaam` typen om het naar een bestand te schrijven:

```bash
grep -E -h -o -w -i "\w*politiek\w*" tvg_111/*.txt | sort | uniq -c | sort > tvg_111-matches-politiek.txt
```

Uiteraard kun je bestanden met opgeslagen resultaten weer verder bewerken en analyseren met `grep` en andere commando's, of in andere programma's.
TODO schrijven naar bestand


<a name="grep-word-sets"></a>
### Zoeken naar woordensets

Reguliere expressies bieden ook een mogelijkheid om meerdere opties van patronen te definieren, met parentheses en het keuze symbool `|`. Zo betekent `(januari|februari|maart)`: match met alle regels waarin het woord *januari* voorkomt, of het woord *februari* of *maart*. Zo kun je dus naar voorkomens van maanden zoeken, , of bijvoorbeeld sets van woorden die kwa onderwerp dicht bij elkaar liggen, zoals *overheid*, *regering* en *kabinet*:

```bash
grep -E -o -w -i "\w*(overheid|regering|kabinet)\w*" tvg_111/*.txt | sort | uniq -c
```

In oudere teksten kom je vaak dubbele klinkers tegen, zoals in *regeering*. Als je zoekt in TvG editie 49, kun je ook *regeering* toevoegen:

```bash
grep -E -o -w -i "\w*(overheid|regeering|regering|kabinet)\w*" tvg_49/*.txt | sort | uniq -c
```

De alternatieven *regering* en *regeering* kun je ook korter noteren door de variatie *ee* en *e* aan te geven:

```bash
grep -E -o -w -i "\w*(overheid|reg(ee|e)ring|kabinet)\w*" tvg_49/*.txt | sort | uniq -c
```

Afhankelijk van je onderzoeksfocus, kun je zelf woordenset en contexten definieren om het corpus te doorzoeken en analyseren. Hou bij welke woorden, sets en contexten je definieert, en sla eventuele resultatenlijsten op in aparte bestanden. Hou in een Google Document bij wat je bevindingen zijn, zodat we die in de discussie kunnen vergelijken.


<a name="grep-words-frequencies"></a>
## Overzicht met woordfrequentielijsten

In deze opdracht leer je hoe je een woordenlijst met frequenties kan maken van tekstuele data, hoe je een stopwoordenlijst kunt maken en die kunt gebruiken om woordenlijsten te filteren. Daarnaast leer je ook om lijsten van bigrammen (woordparen) en trigrammen (sets van drie woorden) te maken.

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

Het commando `awk` kan gebruikt worden om voor een woordenlijst de vorige regel te combineren met de huidige regel van de output, waarmee je bigrammen kunt creeeren. Als je die stap doet voor het filteren van stopwoorden, krijg je bigrammen waarbij beide woorden geen stopwoorden zijn:

```bash
cat tvg_111/*.txt | tr '[:punct:]' ' ' | tr '[:upper:]' '[:lower:]' | tr ' ' '\n' | awk 'prev!="" {print prev,$0} {prev=$0}' | grep -v -w -f stopwoorden_tvg.txt | sort | uniq -c | sort -g
```



+ [Overzicht van datums, jaartallen, periodes en namen](#grep-names-dates)
    + [Zoeken met karaktersets](#grep-character-sets)
    + [Overzicht van datums, jaartallen en periodes](#grep-dates)
    + [Overzicht van namen](#grep-names)
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

