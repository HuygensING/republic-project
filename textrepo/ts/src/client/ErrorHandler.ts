import { Response } from "node-fetch";
import RequestError from "./RequestError";

export default class ErrorHandler {

    private static errorPrefix = 'ERROR';

    public static print(msg: string) {
        console.trace(this.errorPrefix, msg);
    }

    public static handle(msg: string, e: Error) {
        let newLine = ":\n";
        if (e instanceof RequestError) {
            console.trace(this.errorPrefix, msg, newLine, e.message, newLine,  e.responseStatus, e.responseBody);
        } else {
            console.trace(this.errorPrefix, msg + newLine, e);
        }
    }

    public static async throw(msg: string, originalResponse: any) : Promise<never> {
        let reasonText = '';
        if(typeof originalResponse.text === 'function') {
            reasonText = await originalResponse.text();
        } else if (originalResponse.message) {
            reasonText = originalResponse.message;
        } else {
            reasonText = JSON.stringify(originalResponse);
        }
        throw new RequestError(msg, originalResponse.status, reasonText);
    }

}
