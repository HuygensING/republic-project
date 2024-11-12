
SHELL = /bin/bash

export AWKPATH = ../common:.
DATE_INPUT = pv -l annotations-layer_DAT.tsv

DATE_DATA = ../criteria/DAT
REGEXES = ${DATE_DATA}/date_regexes.tsv

.DELETE_ON_ERROR:

DAT-annotations.json : processed_dates.tsv annotations-layer_DAT.tsv
	${DATE_INPUT} | gawk -f ./make-json.awk processed_dates.tsv provenance.tsv - | jq > DAT-annotations.json

unrecognised.tsv : processed_dates.tsv
	<processed_dates.tsv gawk -itsv '!$$3{a[$$2]++}END{PROCINFO["sorted_in"]="@val_num_desc";for(d in a) print a[d], d}' >unrecognised.tsv

processed_dates.tsv : ../ner-output/session_dates.tsv ${REGEXES} process-dates.awk date_variants.tsv annotations-layer_DAT.tsv
	${DATE_INPUT} | gawk -f ./process-dates.awk REPORT=date_fuzzy_report.log date_variants.tsv - >processed_dates.tsv

date_variants.tsv : ${REGEXES} annotations-layer_DAT.tsv
	${DATE_INPUT} | gawk -itsv '{print $$5}' | gawk -f ../common/regex-report ${REGEXES} - >date_variants.tsv

annotations-layer_DAT.tsv : ../ner-output/annotations-layer_DAT.tsv filter_resolution_references.awk
	pv -l ../ner-output/annotations-layer_DAT.tsv | gawk -f filter_resolution_references.awk ../ner-output/annotations-layer_RES.tsv - >annotations-layer_DAT.tsv


