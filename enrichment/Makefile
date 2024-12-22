
.PHONY: all
all :
	cd HOE; make
	cd PER; make
	cd LOC; make
	cd ORG; make
	cd COM; make
	cd DAT; make

archive: all
	tar czf republic_entities.tar.gz ???/???-entities.json ???/???-annotations.json

