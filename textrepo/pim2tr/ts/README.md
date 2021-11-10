# PIM -> TextRepo

Import Pergamon Images (PIM) files and metadata into the Text Repository (TR)
- The environment is configured in docker-compose.yml
- Types and records are imported from a csv file
- The Google auth token can be found as a header in images.diginfra.net/pim requests, after logging in

## Preparation
Remove `.example` postfix from:
- types.csv
- external-identifiers.csv

Modify docker-compose.yml:
- network 
- file names
- env vars
- command (`create-all`, `delete-all`)

## Import
Run:
```
export GOOGLE_AUTHORIZATION='Google <token>'
docker-compose up --build -d
tail -f import.log
```

## Check contents match

To check if the contents in TR match the contents in PIM, run:
```
docker-compose run importer npm run check external-id-type <externalId> <typeName>
```
