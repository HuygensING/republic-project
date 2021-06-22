import {TextRepoModel} from "./TextRepoModel";

export class TextRepoVersion extends TextRepoModel {

    public fileId: string;
    public contents: string;
    public id: string;
    public createdAt: string;
    public contentsSha: string;

    constructor(fileId: string, contents: string,) {
        super();
        this.fileId = fileId;
        this.contents = contents;
    }
}
