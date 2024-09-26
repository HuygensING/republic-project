
SHELL = /bin/bash
export AWKPATH = ../common

HOE-annotations.json HOE-entities.json : annotations_matched_simple.json
	bash ../entity-ids/split_json.sh H HOE annotations_matched_simple.json

annotations_matched_simple.json : hoedanigheden.ipynb
	pipenv run jupyter nbconvert --to notebook --execute --inplace hoedanigheden.ipynb
	pipenv run jupyter nbconvert --clear-output --ClearMetadataPreprocessor.enabled=True --inplace hoedanigheden.ipynb
	touch annotations_matched_simple.json


