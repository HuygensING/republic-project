# Opdracht 2: Normaliseren met Open Refine

+ [Introductie](#intro)
    + [Open Refine](#open-refine)
+ [Indices maken](#grep-indices)
    + [Distributies en dispersie van specifieke woorden](#grep-words-distributions)

TO DO

<a name="open-refine"></a>
## Open Refine


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




