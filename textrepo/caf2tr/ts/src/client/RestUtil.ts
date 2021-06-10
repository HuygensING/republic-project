import fetch, {RequestInit, Response} from "node-fetch";
import {TextRepoModel} from "./textrepo/model/TextRepoModel";
import ErrorHandler from "./ErrorHandler";
import FormData = require("form-data");

export default class RestUtil {
    public static async postResource(url: string, resource: TextRepoModel) {
        const response = await RestUtil.postAsJson(url, resource);
        await RestUtil.checkOk(url, response);
        return await response.json();
    }

    public static async postFormData(url: string, formData: FormData) {

        const requestOptions: RequestInit = {
            method: "POST",
            body: formData
        };

        const response = await fetch(url, requestOptions);

        await RestUtil.checkOk(url, response);
        return await response.json();
    }

    public static async put(url: string, body: string, mimetype: string) {
        const response = await fetch(url, {
            method: 'PUT',
            body: body,
            headers: {'content-type': mimetype}
        });
        await RestUtil.checkOk(url, response);
        return await response.json();
    }

    private static async postAsJson(url: string, resource: any) {
        let json = JSON.stringify(resource);
        return await fetch(url, {
            method: 'POST',
            body: json,
            headers: {'content-type': 'application/json'}
        });
    }

    public static async asJson(response: Response) {
        let contentType = response.headers.get('content-type');
        if ('application/json' !== contentType) {
            throw new Error(`Cannot parse json when content-type: ${contentType}. Body: ${await response.text()}`);
        }
        return response.json();
    }

    public static async checkOk(url: string, response: Response) {
        let expected = [200, 201, 202];
        if (!expected.includes(response.status)) {
            await ErrorHandler.throw(`Expected status of ${expected} but was ${response.status}`, response);
        }
    }


    static async delete(url: string, headers) {
        let response = await fetch(url, {
            headers: headers,
            method: 'DELETE',
        });
        await RestUtil.checkOk(url, response);
        return response;

    }

    public static async wait(ms) {
        return new Promise(resolve => {
            setTimeout(resolve, ms);
        });
    }

}
