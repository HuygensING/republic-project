
SHELL = /bin/bash

export AWKPATH = ../common
DATE_INPUT = pv -l ../ner-output/annotations-layer_DAT.tsv

DATE_DATA = ../criteria/DAT
REGEXES = ${DATE_DATA}/date_regexes.tsv

.DELETE_ON_ERROR:

DAT-annotations.json : processed_dates.tsv
	${DATE_INPUT} | gawk -f ./make-json.awk processed_dates.tsv provenance.tsv - | jq > DAT-annotations.json

unrecognised.tsv : processed_dates.tsv
	<processed_dates.tsv gawk -itsv '!$$3{a[$$2]++}END{PROCINFO["sorted_in"]="@val_num_desc";for(d in a) print a[d], d}' >unrecognised.tsv

processed_dates.tsv : session_dates.tsv ${REGEXES} process-dates.awk date_variants.tsv
	${DATE_INPUT} | gawk -f ./process-dates.awk REPORT=date_fuzzy_report.log date_variants.tsv - >processed_dates.tsv

date_variants.tsv : ${REGEXES}
	${DATE_INPUT} | gawk -itsv '{print $$5}' | gawk -f ${AWKPATH}/regex-report ${REGEXES} - >date_variants.tsv

ES_URL = https://annotation.republic-caf.diginfra.org/elasticsearch
ES_YEAR_SEARCH = ${ES_URL}/session_metadata/_search?_source_includes=date.session_date&size=4000&df=date.session_year&q=
ES_DATE_SELECT = .hits.hits.[]|[._id,._source.date.session_date]|@tsv

session_dates.tsv :
	@rm -f session_dates.tsv
	seq 1560 1800 | while read yr; do \
		curl -s "${ES_YEAR_SEARCH}$$yr" | jq -r "${ES_DATE_SELECT}" >>session_dates.tsv; \
	done

