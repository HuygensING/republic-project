# GNB conversion
Conversion of GNB xml files and mysql database to elasticsearch indices

## Preparation

### Data

- Add source xml files to `./data`
- Add source mysql db to `./data`
- Note: `XmlResolutionConverter` expects source xml path to contain `resoluties_staten_generaal`.

### .env
- Copy `.env.example` to `.env`
- Modify `XML_GLOB`

## Convert

### 1. Start containers
Run:
```
docker-compose up
```

### 2. Prepare mysql and elasticsearch
Run:
```
docker exec -i db mysql -uroot -pexample mysql < statengeneraal20210105-fix.sql 
curl -X PUT 'localhost:9200/gnb-resolutions' -H content-type:application/json -d "@mapping/mapping-resolutions.json" | jq
curl -X PUT 'localhost:9200/gnb-people' -H content-type:application/json -d "@mapping/mapping-people.json" | jq
```

### 3. Convert xml into elasticsearch gnb index
Run:
```
npm install
source .env
npm run conversion
```

### 4. Create new image
Run:
```
TAG=registry.diginfra.net/vlb/gnb-elastic:latest
docker-compose stop
docker commit elastic 
docker save -o ~/data/gnb/gnb-elastic-$TAG.tar gnb-elastic:$TAG
```

## Conversion log

### gnb-elastic-20210311.tar
- add gnb-people mentionedCount and attendantCount to simplify people queries
- add gnb-people searchName

### gnb-elastic-20210305.tar
Includes:
- gnb-people: functions.category string, people.functions.category string
- gnb-resolutions: metadata.resolution follow number, people.president boolean

### gnb-elastic-20210111.tar
Scripts: ~/workspace/gnb/conversion
Versie gebruikt voor demo op 2021-02-03.

### statengeneraal20210105.sql
Includes function categories.

To fix `Unknown collation: 'utf8mb4_0900_ai_ci'`, run:
```
sed -i '' 's/utf8mb4_0900_ai_ci/utf8mb4_unicode_ci/g' data/statengeneraal20210105-fix.sql
```
Source: https://github.com/drud/ddev/issues/1902#issuecomment-546654862
