# Data Scopes

- coherent methods for using digital data in humanities research

## Focus on data interactions:
- it's not about the tools
- many tutorials on the excellent [Programming Historian](https://programminghistorian.org)
- it's about how and why
- translating research questions, assumption and interpretations to data interactions
- consequences of interactions for questions, assumptions and interpretations

## Frameworks:

- Data Scope: select, model, normalise, link, classify
- Other models focusing on process:
    - [Scholarly Primitives](https://www.google.com/sheets/about/) (John Unsworth): discover, annotate, compare, refer, sample, illustrate, represent
    - [Data Visualization](https://www.google.com/sheets/about/) (Ben Fry): acquire, parse, filter, mine, represent, refine, interact

## Tools:

- UNIX Command line tools
    - Windows users: use [Git Bash](https://github.com/git-for-windows/git/releases/download/v2.16.2.windows.1/PortableGit-2.16.2-64-bit.7z.exe) (portable version)
    - Mac users: use Terminal (comes pre-installed) or [iTerm2](https://iterm2.com/)
    - for modelling, selecting, normalizing
- [OpenRefine](http://openrefine.org/download.html)
    - for data normalization and exploration
    - also look at customized distributions and extensions for e.g. LOD, RDF, NER, ...
- [Anaconda](https://anaconda.org/) (Python distribution with many packages and easy installer)
    - for more complex filtering, linking, classifying
    - Jupyter notebook (interactive Python environment in the browser)
- Text Editor:
    - for note taking, inspecting data, ...
    - many good options: [Atom](https://atom.io/), [Notepad++](https://portableapps.com/apps/development/notepadpp_portable), [Sublime](https://www.sublimetext.com/)
- Excel, [Libre Office Calc](https://www.libreoffice.org/discover/calc/) or [Google Spreadsheet](https://www.google.com/sheets/about/)
    - for spreadsheet analysis
    - pivot table for grouping, co-occurrence
- [Voyant Tools](https://voyant-tools.org/)
    - online text analysis tool, *note that this requires uploading your data to the web*
    - for user-friendly exploration of texts

## Modelling:

- "heuristic process of constructing and manipulating models" (McCarty, 2004)
- model: 
    - "a representation of something for purposes of study,"
    - "or a design for realizing something new"
- model determines what aspects of data to focus on
    - structures data in sources around research focus
    - transforms data, affects interpretation!

## Modelling:

- defining data axes: 
    - persons, organisations, locations, dates, topics, 
    - themes, life courses, events, actions, decisions
- defining categories or classes along those axes: 
    - roles of people and organisations
    - periods, regions
    - Research stages:
- model is updated as research progresses
    - this updating reflects growing insights

## Selecting:

- Which materials do I include? Which data elements do I focus on?
    - data axes
- algorithmic selection:
    - everything matching a (set of) keyword(s)
    - documents by type, creator, title, size, ...
- What are consequences of these selections?
    - What am I excluding?

## Normalizing:

- map variation, 
    - essential for next step: linking 

## Linking:

- linking across different corpora
    - e.g. mentions of same person, location, date, ...

## Classifying:



Deel 1:
- vaardigheden:
    - grip krijgen op grote tekstbestanden met grotendeels onbekende inhoud en grote variatie
    - mogelijkheden om patronen te ontdekken
    - gestructureerd omgaan met ongestructureerde data
- Corpus: Tijdschrift voor Geschiedenis

Tijdschrift voor Geschiedenis (TvG):
- edities: 121 (1886-2008)
    - pagina's: 60,751
    - Woorden: totaal = 30,861,146
    - Woorden: uniek = 932,766
- OCR data:
    - incompleet, ongestructureerde tekst, beperkte ontsluiting

UNIX Command Line:
- Exotische commando's en syntax:
    - grep, awk, sed, cat, tr, sort, uniq, paste
- Waarom? Omdat je gelukkig van wordt!
    - generieke toolset voor data exploratie en extractie
    - pipelines voor ketens van stappen
- reguliere expressies 
    - CTRL-F on steroids
    - voor patronen herkennen en transformeren

Hoe hou ik bij wat ik gedaan heb?
- history
- kopieer commando's naar een bestand
- script: UNIX kan bestand met lijst van commando's uitvoeren (herhaalbaarheid)

- We claimen niet dat alle onderzoek voortaan via de command line moet!
    - maar het illustreert goed waar data scopes over gaat: transparent maken van het process



