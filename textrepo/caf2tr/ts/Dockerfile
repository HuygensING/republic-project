FROM node:13.8.0

WORKDIR /caf-tr-import

RUN apt-get update && apt-get install curl -y

COPY ./package.json /caf-tr-import
COPY ./package-lock.json /caf-tr-import
RUN npm install -g ts-node

COPY ./src/ /caf-tr-import/src
COPY ./import.sh /caf-tr-import

RUN npm install
