# Production Build

## Prepare and run prod setup

- Set production build environment variables in `./ui/.env`

- Build in `./ui`:
```
npx react-scripts build
```

- Add build files to remote `./ui`.

- Load remote gnb elastic image tar:
```
docker load < gnb-elastic-<tag>.tar
```

- Start remote containers: 
```
docker-compose up
```
