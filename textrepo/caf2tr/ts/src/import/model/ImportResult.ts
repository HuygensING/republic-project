export default class ImportResult<T> {

    private _successes: T[];
    private _fails: T[];

    constructor(successes: T[], fails: T[]) {
        this._successes = successes;
        this._fails = fails;
    }

    get successes(): T[] {
        return this._successes;
    }
    get fails(): T[] {
        return this._fails;
    }
}
