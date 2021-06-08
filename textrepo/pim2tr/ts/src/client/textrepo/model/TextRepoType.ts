import {TextRepoModel} from "./TextRepoModel";

export default class TextRepoType extends TextRepoModel {
    public name: string;
    public mimetype: string;
    public id: number;

    constructor(name: string, mimetype: string) {
        super();
        this.name = name;
        this.mimetype = mimetype;
    }
}
