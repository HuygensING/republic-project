# CAF -> TextRepo

Import CAF json and metadata into the Text Repository
- The environment is configured using environment variables

## First time
Add files:
- .env

Modify docker-compose.yml:
- network 
- file names
- env vars

Run:
```
docker-compose up --build -d
tail -f import.log
```
