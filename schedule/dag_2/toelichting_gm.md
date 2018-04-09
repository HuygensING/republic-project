
# Data Scopes workshop - opdrachten Generale Missiven

## Beschrijving van de bestanden voor de Generale Missiven opdracht

De opdracht werkt met geselecteerde delen uit de generale missiven. Het gaat om de de indices van de vier uitgegeven delen (8 (RGP GS 193, 1725-1729), 11 (RGP GS 232, 1743-1750), 12 (RGP GS 257, 1750-1755) en 13 (RGP GS 258, 1756-1761).

Van alle gepubliceerde delen van de Generale Missiven zijn gedigitaliseerde versies beschikbaar, die ook online zijn te raadplegen. De tekst van de geselecteerde boeken is met optical character recognition (ocr) omgezet naar machine leesbare tekst. Voor dit onderzoek is gebruik gemaakt van deze ge-ocr-de tekst. De ocr-tekst is kwalitatief acceptabel, maar zoals alle automatisch omgezette tekst bevat ook deze onnauwkeurigheden als gevolg van verkeerd herkende letters (en woorden). De teksten bevatten bovendien andere artefacten zoals pagina headers en nummers en voetnoten.

Waar het de vergelijking van de indices en de tekst betreft, is daarom gebruik gemaakt van deel 13. Dit is de enige uitzondering, aangezien daarvan de digitale tekst (in MSWord documenten) nog aanwezig was. Van deze Word documenten is een ‘platte tekst’ versie gemaakt, zonder Word specifieke opmaak, die verstorend kan werken in het proces. De versie van deel 13 is hierdoor kwalitatief beter dan die van de andere delen, want zowel ocr-fouten als de genoemde artefacten ontbreken.  

De Generale Missiven hebben alle dezelfde soorten indices:
-	Personen
-	Geografische namen
-	Scheepsnamen
-	Zaken

Voor de delen 8, 11 en 12 (en de voorgaande delen, die hier buiten beschouwing zijn gebleven) zijn er slechts de back of book indexen beschikbaar, ook in ocr versie
Ook hier is deel 13 een uitzondering, aangezien hier een MSAccess database beschikbaar was met (per onderdeel) de termen en de verwijzingen naar pagina’s.

### directories

Er zijn twee directory's.

_Originele bestanden_:

De directory originele_bestanden bevat de textfiles van de indices die zijn gegenereerd uit de gedownloade pagina's van de online publicatie. Deze bestanden zijn origineel in de zin dat ze de ruwe tekst bevatten. Het nummer verwijst naar hun RGP deelnummer (zie boven). Ze zijn ingedeeld naar het soort trefwoorden per deel:
- geog is geografische trefwoorden
- pers is persoonstrefwoorden
- schepen is scheepstrefwoorden
- alleen nummer is overige, meest zakentrefwoorden

_Bestanden_

- 193_geog.txt
- 193_pers.txt
- 193_schepen.txt
- 193.txt
- 232_geog.txt
- 232_pers.txt
- 232_schepen.txt
- 232.txt
- 257_geog.txt
- 257_pers.txt
- 257_schepen.txt
- 257.txt

_Bewerkte bestanden_:

De directory bewerkte bestanden bevat 'csv'-versies die zijn gegenereerd uit de ruwe bestanden in de originele_bestanden directory. Ze zijn met automatische middelen opgeschoond en gestructureerd. Dat betekent dat er hier en daar ook fouten in zijn geslopen. Er is geen poging gedaan die met de hand te verbeteren.

De indeling is gelijk aan die van de originele bestanden.
De persoonsnamen zijn automatisch gescoord op de taal van de namen; automatisch toegekende taal en score zijn als aparte kolommen (lang en score) toegevoegd. Daar zitten ook fouten in.
De bestanden zijn aangevuld met de bestanden van deel 13, gegenereerd uit het access bestand. Hier is dus het deelnummer gebruikt, niet het RGP nummer

- 193_geog.csv
- 193_pers.csv
- 193_schepen.csv
- 193.csv
- 232_geog.csv
- 232_pers.csv
- 232_schepen.csv
- 232.csv
- 257_geog.csv
- 257_pers.csv
- 257_schepen.csv
- 257.csv

aangevuld met

- 13_pers.csv
- 13_geo.csv
- 13_schepen.csv
- 13_zaken.csv
