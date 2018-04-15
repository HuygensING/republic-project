# TvG Opdracht deel 1: Greppen in TvG Data

+ [Introductie](#intro)
    + [Data downloaden](#data)
    + [Research focus: wat ga ik onderzoeken?](#focus)
+ [Grip met grep: zoeken in data met behulp van reguliere expressies](#grep)
    + [Command Line: interactie via commando's](#grep-command-line)
+ [Overzicht van varianten en contexten voor specifieke woorden en frases](#grep-words)
    + [Zoeken met woordensets](#grep-word-sets)

Eerdere delen TvG opdracht:

+ [Link naar deel 2 van de TvG opdracht](../dag_1/tvg_opdracht2.md) (dag 1)
+ [Link naar deel 3 van de TvG opdracht](../dag_2/tvg_opdracht3.md) (dag 2)

<a name="intro"></a>
## Introductie

Met deze opdracht ontwikkel je de volgende vaardigheden:

+ grip krijgen op heterogene data met grote variatie
+ identificeren en duiden van patronen
+ gestructureerd omgaan met ongestructureerde data

De TvG Dataset is groot en beperkt gestructureerd. Er liggen talloze inzichten verborgen in de 121 jaargangen, maar de bestaande structuur geeft weinig handvatten om die inzichten naar voren te halen. Hoe kun je van deze brondata een data scope creeeren die verschillende perspectieven op het TvG corpus biedt waarmee je op een transparante manier tot nieuwe inzichten komt?

**Open een document voor het bijhouden van data interacties om tot data scope te komen en overwegingen daarbij.** Gebruik bij voorkeur een nieuw Google Doc in de [workshop drive folder](https://drive.google.com/drive/folders/1R8Rex2v0YwfWhW8omEp0esqBkdX_Ymhr) op Google Drive, zodat alle aantekeningen bij elkaar staan zodat we die aan het eind de dag makkelijk kunnen vergelijken. 

<a name="data"></a>
### Data downloaden

+ Je kunt het [hele TvG corpus als een zip bestand](https://surfdrive.surf.nl/files/index.php/s/MqRVCbAYpQBeEjO) downloaden.
+ Waar staat mijn data?
+ Hoe kan ik met command line tools bij mijn data?
    + commando's worden uitgevoerd vanuit een working directory (folder)
    + je kunt je working directory veranderen ('cd' for change directory)
    + je kunt  aangeven waar een command line tool de data kan vinden t.o.v. je working directory

<a name="focus"></a>
### Research focus: wat ga ik onderzoeken?

_Wat is mijn onderzoeksvraag of thema?_

Probeer eerst vast te stellen wat je wilt onderzoeken. Wat voor mogelijk e.g. historiografische inzichten verwacht je in het TvG corpus te kunnen vinden? De ervaring leert dat je dit tijdens het onderzoeksproces nog regelmatig zal herzien. Initiele aannames en verwachtingen blijken vaak niet goed genoeg op het bestaande materiaal aan te sluiten, waardoor je een onderzoeksvraag wilt aanpassen of over wilt stappen naar een compleet andere vraag. 

Het is vaak inzichtelijk en leerzaam om die momenten van bijsturen en compleet van richting veranderen vast te leggen. Niet alleen hoe je van richting verandert, maar ook waar, wanneer en waarom. Welke stap in het proces en welk aspect van de data leiden tot zo'n verandering?

<a name="focus-selection"></a>
#### Selectie

_Welke informatie uit TvG is daarbij relevant?_ Zijn alle jaargangen relevant (voor e.g. temporeel onderzoek), of slechts een subset. Of kun je dat van te voren nog niet vaststellen?

_Welke jaargangen, pagina's zeggen iets over mijn onderzoeksvraag/thema?_ Tijdens het creeeren van een data scope wil je wellicht specifieke edities, individuele pagina's of pagina-reeksen selecteren om op in te zoomen. Houd bij welke selecties je maakt. 

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

De volgende handige [`grep` cheat sheet](http://www.ericagamet.com/wp-content/uploads/2016/04/Erica-Gamets-GREP-Cheat-Sheet.pdf) geeft een overzicht van alle opties, parameters en patronen je kunt gebruiken in `grep`. Dit is vooral handig als je eenmaal op weg met onderstaande oefeningen en verschillende opties en concepten hebt leren kennen.

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

+ [Link naar deel 2 van de TvG opdracht](../dag_1/tvg_opdracht2.md) (dag 1)

