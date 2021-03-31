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

Run:
```
docker-compose up --build -d
docker-exec -ti importer sh 
```

## Import from csv
```
npm run create-all
```

## Delete from csv
```
npm run delete-all
```

