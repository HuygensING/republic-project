SHELL = /bin/bash
export AWKPATH = ../common:.
.DELETE_ON_ERROR:

LOC_DATA = ../criteria/LOC/

LOC-annotations.json : LOC-entities.json recognised-locations.tsv
	gawk -f mk_annotation_json.awk provenance.step*.tsv recognised-locations.tsv | jq > LOC-annotations.json
LOC-entities.json : loc-entities-full.tsv
	gawk -f mk_entity_json.awk loc-entities-full.tsv | jq > LOC-entities.json

loc-entities-full.tsv : loc-entities.tsv loc-ids.tsv recognised-locations.tsv add_categories.awk
	gawk -f add_categories.awk loc-ids.tsv recognised-locations.tsv loc-entities.tsv > loc-entities-full.tsv

recognised-locations.tsv : annotations-layer_LOC.tsv loc-variants.tsv recognise-locations.*.awk ${LOC_DATA}loc-fuzzy-variants.tsv
	pv -l annotations-layer_LOC.tsv |\
		gawk -f recognise-locations.1.awk |\
		gawk -f recognise-locations.2.awk |\
		gawk -f recognise-locations.3.awk |\
		gawk -f recognise-locations.4.awk >recognised-locations.tsv
	<recognised-locations.tsv gawk -itsv '!$$9{print $$5}' | sort | uniq -c | sort -hr > unrecognised-location-strings.tsv

annotations-layer_LOC.tsv : filter-personal-names.awk personal-names.tsv ../ner-output/annotations-layer_LOC.tsv
	gawk -f filter-personal-names.awk personal-names.tsv ../ner-output/annotations-layer_LOC.tsv > annotations-layer_LOC.tsv

personal-names.tsv : extract-personal-names.awk ../ner-output/annotations-layer_HOE.tsv ../ner-output/annotations-layer_PER.tsv
	gawk -f extract-personal-names.awk ../ner-output/annotations-layer_HOE.tsv ../ner-output/annotations-layer_PER.tsv >personal-names.tsv

loc-variants.tsv: loc-ids.tsv ${LOC_DATA}locations.tsv
	gawk -itsv 'NR==FNR{id[$$1]=$$2;next}FNR==1{next}{gsub(/[~]/,"/",$$1);split($$1,m,/; */);for(i in m)$$5=(i==1?"":$$5"; ")id[m[i]];$$1=$$2=$$3=$$4="";sub(/^\t+/,"")}FNR<NR' loc-ids.tsv ${LOC_DATA}locations.tsv >loc-variants.tsv

loc-ids.tsv : loc-entities.tsv
	<loc-entities.tsv gawk -itsv 'NR>1{print $$1}' | gawk -f ../entity-ids/generate-ids.awk PREFIX=L ../entity-ids/id-list.tsv - >loc-ids.tsv

loc-entities.tsv : ${LOC_DATA}locations.tsv
	gawk -f extract-entities.awk ${LOC_DATA}locations.tsv > loc-entities.tsv

# loc-fuzzy-variants.tsv was generated with
#<match_counts.tsv gawk -itsv '$3>200&&length($2)>5{print$1,$2}' >loc-fuzzy-variants.tsv

