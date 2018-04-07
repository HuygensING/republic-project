# Opdracht 1: Greppen in TvG Data

TO DO

+ keuzes in modelleren
+ definieren data assen
+ bijhouden van data interacties om tot data scope te komen

## Data downloaden

+ Waar staat mijn data?
+ Hoe kan ik met command line tools bij mijn data?
    + commando's worden uitgevoerd vanuit een working directory (folder)
    + je kunt je working directory veranderen ('cd' for change directory)
    + je kunt  aangeven waar een command line tool de data kan vinden t.o.v. je working directory

## Research focus
- wat is mijn onderzoeksvraag of thema?

Selectie:
- welke informatie uit TvG is daarbij relevant?
- welke jaargangen, pagina's zeggen iets over mijn onderzoeksvraag/thema?

Modelleren:
- hoe representeer ik relevante informatie in mijn brondata? 
- Wat mis ik mogelijk? Waar legt mijn keuze de focus op en wat verdwijnt mogelijk naar de achtergrond?


## Reguliere expressies

Open een nieuwe tab in je browser en ga naar [https://regex101.com/](https://regex101.com/).

'''
egrep "politiek" tvg_111/*.txt
'''

'''
egrep --color "politiek" tvg_111/*.txt
'''

'''
egrep --color -w "politiek" tvg_111/*.txt
'''

'''
egrep --color -w "politiek\w+" tvg_111/*.txt
'''

'''
egrep --color -w "\w+politiek" tvg_111/*.txt
'''

'''
egrep --color -o -w "\w+politiek" tvg_111/*.txt
'''

'''
egrep -h -o -w "\w+politiek" tvg_111/*.txt
'''

'''
egrep -h -o -w "\w+politiek" tvg_111/*.txt | sort
'''

'''
egrep -h -o -w "\w+politiek" tvg_111/*.txt | sort | uniq
'''

'''
egrep -h -o -w "\w+politiek" tvg_111/*.txt | sort | uniq -c
'''

'''
egrep -h -o -w "\w+politiek" tvg_111/*.txt | sort | uniq -c | sort
'''

'''
egrep -h -o -w "\w+politiek" tvg_111/*.txt | tr '[:upper:]' '[:lower:]' | sort | uniq -c | sort
'''

'''
egrep -h -o -w "\w+ \w+politiek" tvg_111/*.txt | tr '[:upper:]' '[:lower:]' | sort | uniq -c | sort
'''

'''
egrep -h -o -w "(\w+ ){,2}\w+politiek" tvg_111/*.txt | tr '[:upper:]' '[:lower:]' | sort | uniq -c | sort
'''

'''
egrep -h -o -w "\w*politiek" tvg_111/*.txt | sort | uniq -c | sort
'''

'''
egrep -h -o -w "\w+ \w*politiek" tvg_111/*.txt | sort | uniq -c | sort
'''

'''
egrep -h -o -w "(\w+ ){,2}\w*politiek" tvg_111/*.txt | sort | uniq -c | sort
'''

'''
egrep -h -o -w "(\w+ ){,2}\w*politiek" tvg_111/*.txt | tr '[:upper:]' '[:lower:]' | tr ' ' '\n' | egrep "\w{5,}" | sort | uniq -c | sort
'''


Karaktersets

zoeken naar hoofdletters:

'''
egrep -h --color -w "[A-Z]" tvg_111/*.txt
'''

'''
egrep -h --color -w "[A-Z]{2,3}" tvg_111/*.txt
'''

'''
egrep -h --color -w "[A-Z]{3,}" tvg_111/*.txt
'''

'''
egrep -h --color -w "[A-G]{3,}" tvg_111/*.txt
'''

zoeken naar getallen:
'''
egrep -h --color -w "[0-9]{3,}" tvg_111/*.txt
'''

'''
egrep -h --color -w "1[0-9]{3}" tvg_111/*.txt
'''

zoeken naar combinatiesets van hoofdletters en getallen:
'''
egrep -h --color -w "[A-G0-9]{3,}" tvg_111/*.txt
'''

'''
egrep -h --color -w "[A-Ga-g]{3,}" tvg_111/*.txt
'''

'''
egrep -h --color -w "[A-Ga-g]{3,}" tvg_111/*.txt
'''

zoeken naar woorden die beginnen met een hoofdletter:

'''
egrep -h --color -w "[A-Z]\w+" tvg_111/*.txt
'''

'''
egrep -h --color -w "[A-Z](\w|-)+" tvg_111/*.txt
'''

'''
egrep -h -o -w "[A-Z]\. [A-Z](\w|-)+" tvg_111/*.txt
'''

'''
egrep -h -o -w "[A-Z][a-z]?\. [A-Z](\w|-)+" tvg_111/*.txt
'''

'''
egrep -h -o -w "[A-Z][a-z]?\. [A-Z](\w|-)+" tvg_111/*.txt | sort | uniq -c | sort
'''

We zien nu "F. Van" als meest frequente naam. Dat is waarschijnlijk een incomplete naam. 

'''
egrep -h -o -w "[A-Z][a-z]?\.( [A-Z](\w|-)+)+" tvg_111/*.txt | sort | uniq -c | sort
'''

Bovendien zijn er waarschijnlijk ook veel namen waarbij "van" met kleine letters is geschreven. Andere tussenwoorden die veel voorkomen zijn "de" "der" "den":

'''
egrep -h -o -w "[A-Z][a-z]?\.( van| de| der| den)*( [A-Z](\w|-)+)+" tvg_111/*.txt | sort | uniq -c | sort
'''

Waarschijnlijk zijn er ook namen met meerdere voorletters:

'''
egrep -h -o -w "([A-Z][a-z]?\.)+( van| de| der| den)*( [A-Z](\w|-)+)+" tvg_111/*.txt | sort | uniq -c | sort
'''

Als we willen zijn op welke pagina's die namen voorkomen, kunnen we de optie "-h" weghalen, zodat de bestandsnamen geprint worden:

'''
egrep -o -w "([A-Z][a-z]?\.)+( van| de| der| den)*( [A-Z](\w|-)+)+" tvg_111/*.txt
'''

Resultaten schrijven naar een bestand:

'''
egrep -o -w "([A-Z][a-z]?\.)+( van| de| der| den)*( [A-Z](\w|-)+)+" tvg_111/*.txt > persoonsnamen-tvg_111.txt
'''

'''
egrep -o -w "([A-Z][a-z]?\.)+( van| de| der| den)*( [A-Z](\w|-)+)+" tvg_11[0-9]/*.txt | sed -E 's/.txt:/,/' | sed -E 's/tvg_[0-9]+\///' | sed -E 's/_page/,page/' > tvg_persoonsnamen.txt
'''

gebruik sed om patronen te transformeren (e.g. markeren a la XML):



'''
egrep --colour -w "([A-Z](\.|\w+))+( van| de| der| den)*( [A-Z](\w|-)+)+" tvg_111/*.txt
'''

'''
egrep -o -w "politiek\w+" tvg_111/*.txt
'''


'''
egrep -h --color -w "neutraliteitspolitiek" tvg_*/*.txt | tr -d '[:punct:]' | tr '[:upper:]' '[:lower:]' | tr ' ' '\n' | sort | uniq -c | sort
'''



## Grep

Download de [TvG dataset]. *Voor Windows gebruikers die Git Bash hebben geinstalleerd, sla de dataset op in eennieuwe directory in de directory waar Git Bash is geinstalleerd. Anders kun je vanuit de command line niet bij de data.*

