# GNB xml -> elastic conversion
Conversion of GNB xml files and mysql database to elasticsearch indices

## Data

Add source xml files to `./data`
Note: `XmlResolutionConverter` expects source xml path to contain `resoluties_staten_generaal`:

## .env
Copy `.env.example` to `.env`

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

