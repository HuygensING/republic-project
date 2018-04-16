# TvG Opdracht deel 3: Toegangen maken met Open Refine

+ [Introductie](#intro)
    + [Indices maken](#intro-indices)
    + [Open Refine](#open-refine)
    + [Geprepareerde grep bestanden](#prepared-data)

Eerdere delen TvG opdracht:

+ [Link naar deel 1 van de TvG opdracht](../dag_1/tvg_opdracht1.md)
+ [Link naar deel 2 van de TvG opdracht](../dag_1/tvg_opdracht2.md)

**Open een document voor het bijhouden van data interacties om tot data scope te komen en overwegingen daarbij.** Gebruik bij voorkeur een nieuw Google Doc in de [workshop drive folder](https://drive.google.com/drive/folders/1R8Rex2v0YwfWhW8omEp0esqBkdX_Ymhr) op Google Drive, zodat alle aantekeningen bij elkaar staan zodat we die aan het eind de dag makkelijk kunnen vergelijken. 

<a name="intro-indices"></a>
## Introductie

Met `grep` kun je veel, gevarieerd en interessante output genereren, maar zeker als het veel is, is het soms moeilijk om er verder grip op te krijgen zonder naar het materiaal zelf te gaan. Een van de voordelen om bestandsnamen in de `grep` output te bewaren is dat je daarmee de informatie hebt om van een treffer naar een specifieke pagina in een specifieke editie te gaan. 

Maar de treffers bevatten vaak veel varianten van namen of concepten die je zou willen normaliseren, en wellicht wil je ook meerdere treffers groeperen onder een breder trefwoord. Daar gaat het laatste deel van de TvG opdracht over.

<a name="intro-indices"></a>
### Indices maken

Een mogelijkheid voor het verder bewerken van de `grep` output is om het om te vormen tot een index, waarin je verschillende lagen van structuur kunt aanbrengen. Hiermee creeer je nieuwe ingangen tot het TvG corpus waarmee je (of iemand anders) in verdere analyse makkelijker naar specifieke delen van het materiaal kunt springen voor close reading of selecties kunt maken van pagina's gebaseerd op relevante indextermen voor distant reading. Een handige tool voor dit soort data-transformaties is [Open Refine](http://openrefine.org/).

<a name="open-refine"></a>
### Open Refine

Open Refine lijkt in eerste instantie veel op spreadsheet programma's, maar enige experimentatie ermee laat zien dat het heel andere doeleinden heeft. Net als de UNIX command line tools biedt het eindeloos veel geavanceerde opties om complexe bewerkingen uit te voeren, maar ook een aantal erg simpele maar zeer nuttige opties om data te *normaliseren*, *selecteren*, *linken* en *classificeren* (en zelfs *modelleren*, maar daar besteed deze opdracht geen aandacht aan). 

Ook in Open Refine kun je en zul je op allerlei manieren *reguliere expressies* gebruiken voor de verschillende Data Scope activiteiten. De notatie zal dus hopelijk herkenbaar zijn en steeds vertrouwder voelen. 

Voor raadpleging tijdens en na de opdracht, een handige [cheat sheet voor Open Refine](https://github.com/OpenRefine/OpenRefine/wiki/General-Refine-Expression-Language).

+ stap 1: **project creeeren**: laad een van de bestanden in die je met `grep` hebt gemaakt en gebruik `:` als scheidingsteken (*field separator*). Kijk of in je inputbestand de eerste regel een header is (bij `grep` is dat niet het geval tenzij je die expliciet hebt toegevoegd). Zo niet, haal dan het vinkje weg bij `Parse next 1 lines as column headers`. Klik op `Create project`. Geef eerst de twee kolommen zinnige namen, e.g. `bestandsnaam` en `treffer`: klik op het driehoekje naast de kolomnaam, kies `Edit column > rename this column` en pas de naam aan.
+ stap 2: **indices maken**. Zet editie, paginanumer en matches in aparte kolommen. Behoud daarbij de originele kolommen, kopieer ze en pas de kopieen aan. Zo kun je altijd de originele data terugzien.
    + kopier de kolom met de bestandsnaam naar een extra kolom die je verder kunt bewerken om editie en paginanummer te splitsen. Klik op het driehoekje naast de kolomnaam, kies `Edit column > Add column based on this column...`, kies als kolomnaam `Editie` en klik op `OK`.
    + in de Editie-kolom, klik op het driehoekje naast de kolomnaam en kies `Edit column > Split into several columns...`, vink `regular expression` aan en vul bij separator in `\/tvg_[0-9]+_page_`. De kolommen heten nu `Editie 1` en `Editie 2`. Hernoem de eerste naar `Editie`, de tweede naar `Pagina`.
    + verwijder `.txt` uit de pagina-kolom: `Edit cells > Transform...` en voer in het Expression veld in `value.replace(".txt", "")`. Klik `OK`.
    + Schoon de kolom met treffers op door zgn. *trailing whitespace* te verwijderen: `Edit cells > Common transforms > Trim leading and trailing whitespace`
    + Nu heb je de `grep` output veranderd in een csv bestand met per regel de bestandsnaam waar de treffer uitkomt, de editie, het paginanummer en trefwoord. Dit is vergelijkbaar met een index.
+ stap 3: **termen normaliseren en selecteren**. Creeer een kopie van de kolom met treffers (`Edit column > Add column based on this column`, kies als kolom iets als `Genormaliseerde treffer` en klik `OK`). Kies het `Text facet` voor de gekopieerde kolom met treffers (klik op het driehoek boven de kolom en kies `Facet > Text Facet`). Normaliseer variaties in matches. Verwijder rijen met irrelevant treffers.
+ stap 4: **termen classificeren** Creeer een kopie van de genormaliseerde treffers en noem die `Classificatie`. Vervang n de nieuwe kolom nu termen door bredere labels (wees creatief, wat is een interessante classificatie die iets toevoegt aan de bestaande data?). Je kunt m.b.v. `Text Facet` heel makkelijk rijen selecteren met dezelfde treffer en deze aanpassen in het `Facet/Filter` menu aan de linkerkant (zweef met de muis over een term en klik `edit`). Je kunt meerdere classificaties in dezelfde kolom zetten (bedenk goed wat een handig scheidingsteken is zodat je later de classificaties kunt scheiden) of extra kolommen aanmaken.


<a name="prepared-data"></a>
### Geprepareerde grep bestanden

Hieronder zijn links naar een aantal bestanden met `grep` resultaten die je kunt gebruiken voor bovenstaande opdracht. Bij elk bestand staat de command line opdracht waarmee deze gegenereerd is zodat je het zelf na kunt gaan.

+ [Termen die de string 'politiek' bevatten](tvg_politiek.txt)

```bash
grep -r -E -o "(\w|-)*politiek(\w|-)*" tvg_*/ | grep -v -E "toc\.(csv|xml)" > tvg_politiek.txt
```

+ [Opstanden](tvg_opstand.txt)

```bash
grep -r -E  -o -w "([A-Z](\w|-)+[- ])+[oO]pstand" tvg_*/ | grep -v -E "toc\.(csv|xml)" > tvg_opstand_pre.txt
grep -r -E  -o -w "[oO]pstand( \w+){,3} ([A-Z](\w|-)+ )+" tvg_*/ | grep -v -E "toc\.(csv|xml)" > tvg_opstand_post.txt
cat tvg_opstand_p* > tvg_opstand.txt
```

+ [Oorlogen](tvg_oorlog.txt)

```bash
grep -r -E  --color -o -w "\w+ ([A-Z](\w|-)+[- ])+[oO]orlog" tvg_*/ | grep -v -E "toc\.(csv|xml)" > tvg_oorlog_pre.txt
grep -r -E  --color -o -w "\w+ [oO]orlog( (in|van|met|tussen|tegen)( \w+){,2}) ([A-Z](\w|-)+ )+" tvg_*/ | grep -v -E "toc\.(csv|xml)" > tvg_oorlog_post.txt
cat tvg_oorlog_p* > tvg_oorlog.txt
```

+ [Ministers](tvg_minister.txt)

```bash
grep -r -E  --color -o -w "[mM]inister (([A-Z]\.)+ )*((van|de|den|der|te) )*([A-Z](\w|-)+)( [A-Z](\w|-)+)*" tvg_*/ | grep -v -E "toc\.(csv|xml)" > ../tvg_minister.txt
```

+ [Migratie](tvg_migratie.txt)

```bash
grep -r -E  --color -o -w "([A-Z](\w|-)+ )*(\w|-)+[mM]igra[nt](\w|-)+(( \w+){,2}( [A-Z0-9](\w|-)+)+)*" tvg_*/ | grep -v -E "toc\.(csv|xml)" > tvg_migratie.txt
```

+ [Grondwetten en constituties](tvg_grondwet.txt)

```bash
grep -r -E  --color -o -w "([A-Z](\w|-)+ )*([gG]rondwet|[cC]onstitutie)( van ([A-Z0-9](\w|-)+ )*)*" tvg_*/ | grep -v -E "toc\.(csv|xml)" > tvg_grondwet.txt
```

+ [Termen die de string 'vrouw' bevatten](tvg_vrouw.txt)

```bash
grep -r -E  -i -o "\w*vrouw\w*" tvg_*/ > tvg_vrouw.txt
```

+ [Namen en frases rondom de string 'Oranje'](tvg_oranje.txt)

```bash
grep -r -E  -o -w "([A-Z](\w|-)+[- ])+(\w+[, ]){,3}[oO]ranje([ -][A-Z](\w|-)+)*" tvg_*/ | grep -v -E "toc\.(csv|xml)" > tvg_oranje.txt
```

