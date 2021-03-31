FROM node:15.12-alpine3.10

RUN apk update && apk add curl

COPY ./src/ /pim-tr-import/src
COPY ./package.json /pim-tr-import
COPY ./package-lock.json /pim-tr-import

WORKDIR /pim-tr-import

RUN npm install
RUN npm install -g ts-node
