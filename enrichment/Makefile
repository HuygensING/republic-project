

all : out/LOC-entities.json out/HOE-entities.json out/PER-entities.json out/COM-entities.json out/ORG-entities.json out/LOC-annotations.json out/HOE-annotations.json out/PER-annotations.json out/DAT-annotations.json out/COM-annotations.json out/ORG-annotations.json
	@echo "all are up-to-date"

out/LOC-entities.json : LOC/LOC-entities.json
	cp LOC/LOC-entities.json out/LOC-entities.json
out/HOE-entities.json : HOE/HOE-entities.json
	cp HOE/HOE-entities.json out/HOE-entities.json
out/PER-entities.json : PER/PER-entities.json
	cp PER/PER-entities.json out/PER-entities.json
out/COM-entities.json : COM/COM-entities.json
	cp COM/COM-entities.json out/COM-entities.json
out/ORG-entities.json : ORG/ORG-entities.json
	cp ORG/ORG-entities.json out/ORG-entities.json

out/LOC-annotations.json : LOC/LOC-annotations.json
	gawk -f update_provenance.awk TYPE=LOC LOC/LOC-annotations.json | jq >out/LOC-annotations.json
out/DAT-annotations.json : DAT/DAT-annotations.json
	gawk -f update_provenance.awk TYPE=DAT DAT/DAT-annotations.json | jq >out/DAT-annotations.json
out/COM-annotations.json : COM/COM-annotations.json
	gawk -f update_provenance.awk TYPE=COM COM/COM-annotations.json | jq >out/COM-annotations.json
out/ORG-annotations.json : ORG/ORG-annotations.json
	gawk -f update_provenance.awk TYPE=ORG ORG/ORG-annotations.json | jq >out/ORG-annotations.json
out/HOE-annotations.json : HOE/HOE-annotations.json
	<HOE/HOE-annotations.json gawk '/"provenance"/{print "},"}/tag_length/{sub(/,$$/,"")}1' |\
		gawk -f update_provenance.awk TYPE=HOE DROP=1 - | jq >out/HOE-annotations.json
out/PER-annotations.json : PER/PER-annotations.json
	<PER/PER-annotations.json gawk '/tag_length/{print;print"},\n  \"provenance\": [\n    ]";next}1' |\
		gawk -f update_provenance.awk TYPE=PER DROP=1 - | jq >out/PER-annotations.json


