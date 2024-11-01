
SHELL = /bin/bash
export AWKPATH = ../common:.
.DELETE_ON_ERROR:

COMMON_DATA = ../criteria/common
COMMON_CRITERIA = ${COMMON_DATA}/afkortingen.tsv ${COMMON_DATA}/fuzzy-corrections.tsv ${COMMON_DATA}/simplify.tsv ${COMMON_DATA}/spelling-regexes.tsv ${COMMON_DATA}/split.tsv

ANNOTS = annotations-layer_COM.tsv

COM-annotations.json COM-entities.json : COM-annotations.joined.json
	bash ../entity-ids/split_json.sh C COM COM-annotations.joined.json

COM-annotations.joined.json : koppeling-commissies.ipynb ${ANNOTS}
	pipenv run jupyter nbconvert --to notebook --execute --inplace koppeling-commissies.ipynb
	pipenv run jupyter nbconvert --clear-output --ClearMetadataPreprocessor.enabled=True --inplace koppeling-commissies.ipynb
	touch COM-annotations.joined.json

${ANNOTS} : ../ner-output/${ANNOTS} ${COMMON_CRITERIA}
	gawk -f ../common/improve-ner-output.awk ../ner-output/${ANNOTS} | pv -l >${ANNOTS}


