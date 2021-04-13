export default class RequestError extends Error {
    private _responseStatus: number;
    private _responseBody: string;

    constructor(message: string, responseStatus: number, responseBody: string) {
        super(message);
        this._responseStatus = responseStatus;
        this._responseBody = responseBody;
        Object.setPrototypeOf(this, new.target.prototype);
    }
    get responseStatus(): number {
        return this._responseStatus;
    }

    get responseBody(): string {
        return this._responseBody;
    }
}
