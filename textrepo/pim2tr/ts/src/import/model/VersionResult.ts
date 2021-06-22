import {TextRepoVersion} from "../../client/textrepo/model/TextRepoVersion";

export class VersionResult extends TextRepoVersion {
    private _pimTranscriptionUuid: string;
    private _metadata: object;

    get pimTranscriptionUuid(): string {
        return this._pimTranscriptionUuid;
    }

    set pimTranscriptionUuid(pimImageUuid: string) {
        this._pimTranscriptionUuid = pimImageUuid;
    }

    get metadata(): object {
        return this._metadata;
    }

    set metadata(value: object) {
        this._metadata = value;
    }
}
