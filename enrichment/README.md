
# REPUBLIC entities

- [Organisation](#organisation)
- [Input format](#input-format)
- [Output formats](#output-formats)
- [Logging and debugging](#logging-and-debugging)

This directory holds the second part of the REPUBLIC entity enrichment step.
Starting from text fragments identified as _references_ to entities, it carries 
out the two-fold task of _identifying_ the entities present in the input 
material and _resolving_ forementioned references to the identified entities.

The process is fully automatic: after providing the [input 
files](#input-format), `cd` into this directory and issue `Make`.
Individual entity types can be processed by changing into their respective 
subdirectories and then issueing the same command.

## Organisation

An attempt has been made to separate program logic from the criteria used in 
recognising and resolving entity references.
Hence, the top-level subdirectories hold entity-specific code, while criteria 
are (mostly) located in subdirectories of `criteria/`.
Of course, such a separation can only be made partially; it has mostly been 
succesful for those criteria consisting of lists of keywords.
Code and criteria used by multiple entity types can be found in the `common/` 
subdirectories; in general, however, approaches and strategies differ between 
entity types.

The following entity types are present:

| Type   | Description      |
| :-     | :-               |
| `COM/` | Committees       |
| `DAT/` | Resolution dates |
| `HOE/` | Attributions     |
| `LOC/` | Locations        |
| `ORG/` | Organisations    |
| `PER/` | Personal names   |

A central component to most entity types is the parallel fuzzy matcher found in 
`common/edit-distance.awk`. The purpose of this library is choosing a single 
match from a large number of keywords; searches of this kind are used for 
a variety of purpose throughout the entity resolution process.

The library `common/provenance.awk` provides a common format for the automated 
provenance records included with every annotation. These take the form of 
a decision journal, with four-field entries:

| Key        | Purpose                        |
| :-         | :-                             |
| source     | the text operated on           |
| criterium  | the criterium or test applied  |
| evaluation | the result (match) of the test |
| conclusion | a description of the operation |

## Input format

For every entity type, an input file should be present in the `ner-output/` 
folder. The expected filename is `annotations-layer_XXX.tsv`, and the expected 
columns are `layer`, `inv`, `resolution_id`, `paragraph_id`, `tag_text`, 
`offset`, `end` end `tag_length`.

In these input files, the `tag_text` field should contain a textual fragment 
identified as a likely candidate for the given entity type, with the other 
fields documenting its origin.
Regrettably, the fields should be present in the exact order given above, as 
hard-coded column indices are sometimes used.

## Output formats

The final output should consist of two files: one file `XXX-annotations.json` 
holding resolved entity references and one file `XXX-entities.json` holding 
entity metadata. The identifiers connecting the two are generated in a somewhat 
crude way by the scripts in the `entity-ids/` subdirectory: their generation 
depends on a list of previously-assigned ids. Renaming an entity will result in 
a change of identifier.

## Logging and debugging

Wherever the parallel fuzzy matcher is used, reports of succesful matches are 
generated. After editing any keyword lists, studying changes to these log files 
is strongly recommended.

For a quick comparison of subsequent editions, the script 
`compare-annotations.sh` outputs an overview of changed entity assignments.



