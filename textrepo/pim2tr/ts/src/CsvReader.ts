import * as fs from "fs";
import parse = require("csv-parse");

const getStream = require('get-stream');

export default class CsvReader {
    private path: string;
    constructor(path: string) {
        this.path = path
    }

    public async read() {
        const parser = parse({columns: true});
        return getStream.array(fs.createReadStream(this.path).pipe(parser));
    }

}
