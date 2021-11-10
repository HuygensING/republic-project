export default class ConvertResult<T> {

    /**
     * Was conversion successfull?
     */
    private _success: boolean;

    /**
     * Succesfully converted:
     */
    private _results: T[] = [];

    /**
     *Failed to convert:
     */
    private _failed: T[] = [];

    get isSuccess() : boolean {
        return this._success;
    }

    get results(): T[] {
        return this._results;
    }

    get failed(): T[] {
        return this._failed;
    }

    set success(value: boolean) {
        this._success = value;
    }
    set failed(value: T[]) {
        this._failed = value;
    }
    set results(value: T[]) {
        this._results = value;
    }
}
