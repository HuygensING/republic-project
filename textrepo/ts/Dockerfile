FROM node:13.8.0

WORKDIR /pim-tr-import

RUN apt-get update && apt-get install curl -y

COPY ./package.json /pim-tr-import
COPY ./package-lock.json /pim-tr-import
RUN npm install -g ts-node

COPY ./src/ /pim-tr-import/src
COPY ./import.sh /pim-tr-import

RUN npm install
