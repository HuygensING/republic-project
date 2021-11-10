# GNB xml -> elastic conversion
Conversion of GNB xml files and mysql database to elasticsearch indices

## .env
The Importer expects a number environment variables to be set.
Below an example .env file with those env vars, including some example values:

```
# make sure glob contains 'resoluties_staten_generaal':
export XML_GLOB=./data/resoluties_staten_generaal_1626-1630/16*/**/*.xml

# Elasticsearch api version to use:
export ES_VERSION=7.x

# Host of elasticsearch:
export ES_HOST=localhost:9200

# Index names:
export RESOLUTION_INDEX=gnb-resolutions
export PERSON_INDEX=gnb-people

# Mysql host, user, password and database:
export MYSQL_CONNECTION=mysql://root:example@localhost:3306/statengeneraal

# Date format used in resolution and people indices:
export DATE_FORMAT=YYYY-MM-DD
```

## Start containers
Run:
```
docker-compose up
```

## Prepare mysql and elasticsearch
Run:
```
docker exec -i db mysql -uroot -pexample mysql < ~/data/gnb/statengeneraal20210105-fix.sql 
curl -X PUT 'localhost:9200/gnb-resolutions' -H content-type:application/json -d "@mapping/mapping-resolutions.json" | jq
curl -X PUT 'localhost:9200/gnb-people' -H content-type:application/json -d "@mapping/mapping-people.json" | jq
```

## Convert xml into elasticsearch gnb index
Run:
```
npm install
source .env
npm run conversion
```

## Create new image
```
TAG=<tag>
docker-compose stop
docker commit elastic gnb-elastic:$TAG
docker save -o ~/data/gnb/gnb-elastic-$TAG.tar gnb-elastic:$TAG
cp result.log ~/data/gnb/gnb-elastic-$TAG.log
vim ~/data/gnb/README.md
```

