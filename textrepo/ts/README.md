# PIM -> TextRepo

Import PIM files and metadata into the Text Repository
- The environment is configured using environment variables
- Types and records are imported from a csv file


## First time
Add files:
- types.csv
- external-identifiers.csv
- .env

Modify docker-compose.yml:
- network 
- file names
- env vars
- command (`create-all`, `delete-all`)

Run:
```
 export GOOGLE_AUTHORIZATION='Google <token>'
docker-compose up --build -d
```

## Check contents match

To check if the contents in TR match the contents in PIM, run:
```
docker-compose run importer npm run check external-id-type <externalId> <typeName>
```
