# CAF -> TextRepo

Import CAF json and metadata into the Text Repository
- The environment is configured using environment variables

## First time
Create files and dirs:
- `.env`
- `./tmp`

Modify docker-compose.yml:
- network 
- file names
- env vars

Run:
```
docker-compose up --build -d
tail -f import.log
```
