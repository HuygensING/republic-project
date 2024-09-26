
SHELL = /bin/bash
export AWKPATH = ../common:.

PER-annotations.json PER-entities.json : annotations_matched_simple.json
	bash ../entity-ids/split_json.sh P PER annotations_matched_simple.json
	gawk -f capitalise_names.awk PER-entities.json | sponge PER-entities.json

annotations_matched_simple.json : personen.ipynb
	pipenv run jupyter nbconvert --to notebook --execute --inplace personen.ipynb
	pipenv run jupyter nbconvert --clear-output --ClearMetadataPreprocessor.enabled=True --inplace personen.ipynb
	touch annotations_matched_simple.json


