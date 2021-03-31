# PIM -> TextRepo

Import PIM files and metadata into the Text Repository
- The environment is configured using environment variables
- Types and records are imported from a csv file

## First time
Run:
```
npm install
npm install -g ts-node
```

## Import from csv
```
source ../.env && npm run create-all
```
See also: **.env**

## Delete from csv
```
source ../.env && npm run delete-all
```
See also: **.env**

## .env

A number of environment variables are expected:

```
 # Pergamon images host:
 export PIM='https://images.diginfra.net'

 # Pergamon images authorization header value:
 export GOOGLE_AUTHORIZATION='Google <uuid>'

 # Csv with identifiers to create and import from pim:
 export SUBSET_CSV='../external-identifiers.csv'
 
 # Csv with types to create (or to get IDs from)
 export TYPE_CSV='../types.csv'

 # Where to put temporary files:
 export TMP='./tmp'

 # Text Repository host:
 export TR='http://localhost:8080/textrepo'
```

