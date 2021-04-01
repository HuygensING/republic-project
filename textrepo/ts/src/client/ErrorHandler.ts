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

    public static async catch(reason: Response) : Promise<never> {
        let reasonText = '';
        if(typeof reason.text === 'function') {
            reasonText = await reason.text();
        }
        let msg = `Failed to request ${JSON.stringify(reason.url)}`;
        throw new RequestError(msg, reason.status, reasonText);
    }

}
