# TvG Opdracht 2: Toegangen maken met Open Refine

+ [Introductie](#intro)
    + [Open Refine](#open-refine)
+ [Indices maken](#grep-indices)
    + [Distributies en dispersie van specifieke woorden](#grep-words-distributions)

[Link naar deel 1 van de TvG opdracht](../dag_1/tvg_opdracht1.md)

**Open een document voor het bijhouden van data interacties om tot data scope te komen en overwegingen daarbij.** Gebruik bij voorkeur een nieuw Google Doc in de [workshop drive folder](https://drive.google.com/drive/folders/1R8Rex2v0YwfWhW8omEp0esqBkdX_Ymhr) op Google Drive, zodat alle aantekeningen bij elkaar staan zodat we die aan het eind de dag makkelijk kunnen vergelijken. 

<a name="open-refine"></a>
## Open Refine

TO DO: intro Open Refine

<a name="grep-indices"></a>
## Indices maken

TO DO

<a name="grep-words-distributions"></a>
### Distributies en dispersie van specifieke woorden


TO DO:

```bash
grep -E --color -o -w "([A-Z](\w|-)+ )+[A-Z](\w|-)+" tvg_11*/*.txt | sed -E 's/ /_/g' | sed -E s'/\/tvg_[0-9]+_page_/ /' | sed -E 's/\.txt:/ /' > tvg_110-119-namen.csv
```

+ uitzoomen naar hele TvG dataset: grep -r ./
+ de context van termen in TvG:
    + breng contexttermen in kaart per editie, vergelijk over edities
    + breng contexttermen in kaart per decennium, vergelijk over decennia
+ verspreiding van termen binnen een editie
+ verspreiding van termen over edities




