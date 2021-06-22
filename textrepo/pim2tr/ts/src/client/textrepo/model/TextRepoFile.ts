import {TextRepoModel} from "./TextRepoModel";

export default class TextRepoFile extends TextRepoModel {
    public docId: string;
    public typeId: number;
    public id: string;

    constructor(docId: string, typeId: number) {
        super();
        this.docId = docId;
        this.typeId = typeId;
    }
}
