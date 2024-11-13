
SHELL = /bin/bash
export AWKPATH = ../common:.
.DELETE_ON_ERROR:

COMMON_DATA = ../criteria/common
COMMON_CRITERIA = ${COMMON_DATA}/afkortingen.tsv ${COMMON_DATA}/fuzzy-corrections.tsv ${COMMON_DATA}/simplify.tsv ${COMMON_DATA}/spelling-regexes.tsv ${COMMON_DATA}/split.tsv

ANNOTS = annotations-layer_ORG.tsv

ORG-annotations.json ORG-entities.json : ORG-annotations.joined.json
	bash ../entity-ids/split_json.sh O ORG ORG-annotations.joined.json

ORG-annotations.joined.json : koppeling-instellingen.ipynb ${ANNOTS}
	pipenv run jupyter nbconvert --to notebook --execute --inplace koppeling-instellingen.ipynb
	pipenv run jupyter nbconvert --clear-output --ClearMetadataPreprocessor.enabled=True --inplace koppeling-instellingen.ipynb
	touch ORG-annotations.joined.json

locations.tsv : ../LOC/recognised-locations.tsv
	cut -f 4,5,6,7,9,10 ../LOC/recognised-locations.tsv  | gawk -itsv '$$5&&$$5!~/;|NOMATCH/' > locations.tsv

${ANNOTS} : ../ner-output/${ANNOTS} ${ORGMON_CRITERIA}
	gawk -f ../common/improve-ner-output.awk ../ner-output/${ANNOTS} | pv -l >${ANNOTS}


