# Opdracht 1: Greppen in TvG Data

[Introduction](#intro)
[Data downloaden](#data)
[Research focus](#focus)
[Reguliere expressies](#regex)
    + [Oefenen met reguliere expressies](#regex-train)
[Grep: zoeken in data met behulp van reguliere expressies](#grep)
    + [Command Line: ](#command-line)

## Introductie <a name="intro"></a>

Met deze opdracht ontwikkel je de volgende vaardigheden:

+ grip krijgen op heterogene data met grote variatie
+ identificeren en duiden van patronen
+ gestructureerd omgaan met ongestructureerde data

De TvG Dataset is groot en beperkt gestructureerd. Er liggen talloze inzichten verborgen in de 121 jaargangen, maar de bestaande structuur geeft weinig handvatten om die inzichten naar voren te halen. Hoe kun je van deze brondata een data scope creeeren die verschillende perspectieven op het TvG corpus biedt waarmee je op een transparante manier tot nieuwe inzichten komt?

TO DO

+ keuzes in modelleren
+ definieren data assen
+ bijhouden van data interacties om tot data scope te komen

## Data downloaden <a name="data"></a>

+ Waar staat mijn data?
+ Hoe kan ik met command line tools bij mijn data?
    + commando's worden uitgevoerd vanuit een working directory (folder)
    + je kunt je working directory veranderen ('cd' for change directory)
    + je kunt  aangeven waar een command line tool de data kan vinden t.o.v. je working directory

Download de [TvG dataset]. *Voor Windows gebruikers die Git Bash hebben geinstalleerd, sla de dataset op in eennieuwe directory in de directory waar Git Bash is geinstalleerd. Anders kun je vanuit de command line niet bij de data.*

## Research focus <a name="focus">

- wat is mijn onderzoeksvraag of thema?

Selectie:
- welke informatie uit TvG is daarbij relevant?
- welke jaargangen, pagina's zeggen iets over mijn onderzoeksvraag/thema?

Modelleren:
- hoe representeer ik relevante informatie in mijn brondata? 
- Wat mis ik mogelijk? Waar legt mijn keuze de focus op en wat verdwijnt mogelijk naar de achtergrond?

## Reguliere expressies <a name="regex">

### Oefenen met reguliere expressies <a name="regex-train">

Open een nieuwe tab in je browser en ga naar [https://regex101.com/](https://regex101.com/).


## Grep: zoeken in data met behulp van reguliere expressies <a name="grep">

`grep`` is een UNIX command line tool waarmee je kunt zoeken in data-bestanden naar regels die *matchen* met een reguliere expressie (_G_lobally search a _r_egular _e_xpression and _p_rint).

Eerst wat uitleg over de *command line* en hoe je navigeert naar verschillende mappen of directories op je harde schijf en andere aangesloten opslagmedia.

### Command line <a name="command-line">

De command line is een alternatieve manier om te interacteren met de computer. I.p.v. opdrachten geven met de muis, geef je via de command line opdrachten d.m.v. commando's. Alhoewel dit voor veel mensen wennen is aan ongebruikelijke notatie en de onverbiddelijke precisie die vereist is, heeft het ook een aantal voordelen:

+ complexe commando's: het is mogelijk om commando's samen te stellen zodat in 1 regel meerdere opdrachten worden gegeven die achter elkaar worden uitgevoerd.
+ herhaalbaarheid: uitgevoerde opdrachten worden bewaard waardoor je makkelijk eerdere commando's nog een keer kunt uitvoeren. Dit is vooral handig voor complexe commando's of wanneer je een opdracht wilt herhalen met een kleine wijziging.
+ automatisering: je kunt de commando's bewaren in een bestand, zodat je op een later tijdstip kunt zien wat je eerder gedaan hebt. Daarnaast kun je lijsten van commando's in een bestand ook weer achter elkaar laten uitvoeren door het bestand `executable` te maken.

Voor transparant werken met data is het belangrijk en waardevol om uitgevoerde opdrachten bij te houden en te kunnen delen (ook met jezelf op een later tijdstip).

+ navigeren tussen directories
    + `pwd` print working directory: waar ben ik?
    + `ls` list: wat zit er in deze directory?
+ relatieve paden
    + `ls tvg/`: 
    + `ls ../`: 



```bash
egrep "politiek" tvg_111/*.txt
```

```bash
egrep --color "politiek" tvg_111/*.txt
```

```bash
egrep --color -w "politiek" tvg_111/*.txt
```

```bash
egrep --color -w "politiek\w+" tvg_111/*.txt
```

```bash
egrep --color -w "\w+politiek" tvg_111/*.txt
```

```bash
egrep --color -o -w "\w+politiek" tvg_111/*.txt
```

```bash
egrep -h -o -w "\w+politiek" tvg_111/*.txt
```

```bash
egrep -h -o -w "\w+politiek" tvg_111/*.txt | sort
```

```bash
egrep -h -o -w "\w+politiek" tvg_111/*.txt | sort | uniq
```

```bash
egrep -h -o -w "\w+politiek" tvg_111/*.txt | sort | uniq -c
```

```bash
egrep -h -o -w "\w+politiek" tvg_111/*.txt | sort | uniq -c | sort
```

```bash
egrep -h -o -w "\w+politiek" tvg_111/*.txt | tr '[:upper:]' '[:lower:]' | sort | uniq -c | sort
```

```bash
egrep -h -o -w "\w+ \w+politiek" tvg_111/*.txt | tr '[:upper:]' '[:lower:]' | sort | uniq -c | sort
```

```bash
egrep -h -o -w "(\w+ ){,2}\w+politiek" tvg_111/*.txt | tr '[:upper:]' '[:lower:]' | sort | uniq -c | sort
```

```bash
egrep -h -o -w "\w*politiek" tvg_111/*.txt | sort | uniq -c | sort
```

```bash
egrep -h -o -w "\w+ \w*politiek" tvg_111/*.txt | sort | uniq -c | sort
```

```bash
egrep -h -o -w "(\w+ ){,2}\w*politiek" tvg_111/*.txt | sort | uniq -c | sort
```

```bash
egrep -h -o -w "(\w+ ){,2}\w*politiek" tvg_111/*.txt | tr '[:upper:]' '[:lower:]' | tr ' ' '\n' | egrep "\w{5,}" | sort | uniq -c | sort
```

### Zoeken naar woordensets

Je kunt ook patronen definieren voor bijvoorbeeld sets van woorden die kwa betekenis dicht bij elkaar liggen, zoals *overheid*, *regering* en *kabinet*:

```bash
cat tvg_111/*.txt | egrep -o -w -i "\w*(overheid|regering|kabinet)\w*" | sort | uniq -c
```

In oudere teksten kom je vaakk *regeering* tegen. Als je zoekt in TvG editie 49, kun je ook *regeering* toevoegen:

```bash
cat tvg_49/*.txt | egrep -o -w -i "\w*(overheid|regeering|regering|kabinet)\w*" | sort | uniq -c
```

De alternatieven *regering* en *regeering* kun je ook korter noteren door de variatie *ee* en *e* aan te geven:

```bash
cat tvg_49/*.txt | egrep -o -w -i "\w*(overheid|reg(ee|e)ring|kabinet)\w*" | sort | uniq -c
```


### Zoeken met karaktersets

Je kunt ook sets van karakters opgeven als zoekpatroon. Bijvoorbeeld, `[a-z]` geeft aan *alle karakters van a tot en met z*, of `[a-p]` voor *alle karakters van a tot en met p*. Dit is hoofdlettergevoelig (tenzij je met `grep` de optie `-i` gebruikt voor *case-insensitive*), dus `[a-z]` is anders dan `[A-Z]`. Cijfers kunnen ook in sets gedefinieerd worden: `[0-9]` voor *0 tot en met 9* of `[2-4]` voor *2 tot en met 4*. Het is ook mogelijk om sets te maken met combinaties van kleine en hoofdletters en cijfers, e.g. `[a-gD-J3-7]` of `D-J3-7a-g]` (de volgorde van de subsets maakt niet uit).

zoeken naar losse hoofdletters:

```bash
egrep -h --color -w "[A-Z]" tvg_111/*.txt
```

Zoeken naar woorden bestaande uit 2 of 3 hoofdletters:

```bash
egrep -h --color -w "[A-Z]{2,3}" tvg_111/*.txt
```

Zoeken naar woorden bestaande 3 of meer hoofdletters:

```bash
egrep -h --color -w "[A-Z]{3,}" tvg_111/*.txt
```

Zoeken naar woorden bestaande 3 of meer hoofdletters in de set *A tot en met G*:

```bash
egrep -h --color -w "[A-G]{3,}" tvg_111/*.txt
```

Zoeken naar woorden bestaande uit 2 of 3 hoofdletters afgewisseld met punten:

```bash
egrep -h --color -w "([A-Z]\.){2,3}" tvg_111/*.txt
```

Dit zouden afkortingen kunnen zijn, maar lijken ook wel de voorletters van namen. Hier komen we zo op terug. Eerst nog wat andere voorbeelden van karaktersets proberen.

Zoeken naar getallen met tenminste 3 cijfers:

```bash
egrep -h --color -w "[0-9]{3,}" tvg_111/*.txt
```

Zoeken naar jaartallen:

```bash
egrep -h --color -w "1[0-9]{3}" tvg_111/*.txt
```

Zoeken naar combinatiesets van hoofdletters en getallen:

```bash
egrep -h --color -w "[A-G0-9]{3,}" tvg_111/*.txt
```

### Zoeken naar namen

Zoeken naar woorden die beginnen met een hoofdletter:

```bash
egrep -h --color -w "[A-Z]\w+" tvg_111/*.txt
```

Het resultaat levert allerlei namen op, maar ook de eerste woorden van zinnen, die immers ook met een hoofdletter beginnen.

Zoeken naar woorden die beginnen met een hoofdletter en een verbindingsteken mogen bevatten:

```bash
egrep -h --color -w "[A-Z](\w|-)+" tvg_111/*.txt
```

Dit levert ook samengestelde namen op, zoals Noord-Nederland. 

Zoeken naar een hoofdletter gevolgd door een punt, een spatie en dan een woord beginnend met een hoofdletter:

```bash
egrep -h -o -w "[A-Z]\. [A-Z](\w|-)+" tvg_111/*.txt
```

Dit levert een lijst van persoonsnamen op. Waarschijnlijk zijn dit veelal auteurs van de verschillende artikelen, mededelingen en besproken boeken.

Soms word een voornaam afgekort tot twee letters, zoals *Th*. Het volgende patroon is voor zowel voornamen afgekort met een enkele hoofdletter als voor voornamen afgekort met een hoofdletter en een kleine letter:

```bash
egrep -h -o -w "[A-Z][a-z]?\. [A-Z](\w|-)+" tvg_111/*.txt
```

Deze namen kun je sorteren en tellen met een combinatie van `sort` en `uniq`:

```bash
egrep -h -o -w "[A-Z][a-z]?\. [A-Z](\w|-)+" tvg_111/*.txt | sort | uniq -c | sort
```

We zien nu "F. Van" als meest frequente naam. Dat is waarschijnlijk een incomplete naam. 

```bash
egrep -h -o -w "[A-Z][a-z]?\.( [A-Z](\w|-)+)+" tvg_111/*.txt | sort | uniq -c | sort
```

Bovendien zijn er waarschijnlijk ook veel namen waarbij "van" met kleine letters is geschreven. Andere tussenwoorden die veel voorkomen zijn "de" "der" "den":

```bash
egrep -h -o -w "[A-Z][a-z]?\.( van| de| der| den)*( [A-Z](\w|-)+)+" tvg_111/*.txt | sort | uniq -c | sort
```

Waarschijnlijk zijn er ook namen met meerdere voorletters:

```bash
egrep -h -o -w "([A-Z][a-z]?\.)+( van| de| der| den)*( [A-Z](\w|-)+)+" tvg_111/*.txt | sort | uniq -c | sort
```

Als we willen zijn op welke pagina's die namen voorkomen, kunnen we de optie "-h" weghalen, zodat de bestandsnamen geprint worden:

```bash
egrep -o -w "([A-Z][a-z]?\.)+( van| de| der| den)*( [A-Z](\w|-)+)+" tvg_111/*.txt
```

### Zoekresultaten opslaan in een bestand

Resultaten schrijven naar een bestand:

```bash
egrep -o -w "([A-Z][a-z]?\.)+( van| de| der| den)*( [A-Z](\w|-)+)+" tvg_111/*.txt > persoonsnamen-tvg_111.txt
```

```bash
egrep -o -w "([A-Z][a-z]?\.)+( van| de| der| den)*( [A-Z](\w|-)+)+" tvg_11[0-9]/*.txt | sed -E 's/.txt:/,/' | sed -E 's/tvg_[0-9]+\///' | sed -E 's/_page/,page/' > tvg_persoonsnamen.txt
```

gebruik sed om patronen te transformeren (e.g. markeren a la XML):



```bash
egrep --colour -w "([A-Z](\.|\w+))+( van| de| der| den)*( [A-Z](\w|-)+)+" tvg_111/*.txt
```

```bash
egrep -o -w "politiek\w+" tvg_111/*.txt
```


```bash
egrep -h --color -w "neutraliteitspolitiek" tvg_*/*.txt | tr -d '[:punct:]' | tr '[:upper:]' '[:lower:]' | tr ' ' '\n' | sort | uniq -c | sort
```



