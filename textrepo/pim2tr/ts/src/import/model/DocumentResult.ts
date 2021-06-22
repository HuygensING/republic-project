import TextRepoDocument from "../../client/textrepo/model/TextRepoDocument";

export class DocumentResult extends TextRepoDocument {
    private _metadata: object;

    get metadata(): object {
        return this._metadata;
    }

    set metadata(value: object) {
        this._metadata = value;
    }

}
