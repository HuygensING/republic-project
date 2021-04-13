import {TextRepoModel} from "../../client/textrepo/model/TextRepoModel";

export default class ImportResult<T extends TextRepoModel> {

    private _results: T[];
    private _succes: boolean;

    constructor(succes: boolean, results: T[]) {
        this._succes = succes;
        this._results = results;
    }

    public isSuccesful() : boolean {
        return this._succes;
    }

    get results(): T[] {
        return this._results;
    }
}
