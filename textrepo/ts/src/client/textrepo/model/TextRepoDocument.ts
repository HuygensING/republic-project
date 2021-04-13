import {TextRepoModel} from "./TextRepoModel";

export default class TextRepoDocument extends TextRepoModel {
    public externalId: string;
    public id: string;

    constructor(externalId: string) {
        super();
        this.externalId = externalId;
    }
}
