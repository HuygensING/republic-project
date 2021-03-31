import Config from "../../Config";
import * as fs from "fs";
import {DocumentImageSetResource} from "./DocumentImageSetResource";

export default class DocumentImageSetResourceDummy implements DocumentImageSetResource {

    private path: string = Config.TMP + '/documentimageset.json';

    public async getAll() {
        let fileContents = fs.readFileSync(this.path);
        return JSON.parse(fileContents.toString());
    }
}
