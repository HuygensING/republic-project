import TextRepoDocument from "../../client/textrepo/model/TextRepoDocument";

export class ImportEndpointResult extends TextRepoDocument {
    private _documentId: string;
    private _fileId: string;
    private _versionId: string;

    get versionId(): string {
        return this._versionId;
    }

    set versionId(value: string) {
        this._versionId = value;
    }
    get fileId(): string {
        return this._fileId;
    }

    set fileId(value: string) {
        this._fileId = value;
    }
    get documentId(): string {
        return this._documentId;
    }

    set documentId(value: string) {
        this._documentId = value;
    }

}
