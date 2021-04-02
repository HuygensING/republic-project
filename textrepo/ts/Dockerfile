FROM node:13.8.0

RUN apt-get update && apt-get install curl -y

COPY ./src/ /pim-tr-import/src
COPY ./package.json /pim-tr-import
COPY ./package-lock.json /pim-tr-import
COPY ./tsconfig.json /pim-tr-import

WORKDIR /pim-tr-import

RUN npm install -g typescript
RUN npm install -g ts-node
RUN npm install
