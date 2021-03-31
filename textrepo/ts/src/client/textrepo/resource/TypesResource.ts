import fetch from 'node-fetch';
import RestUtil from "../../RestUtil";
import TextRepoType from "../model/TextRepoType";
import ErrorHandler from "../../ErrorHandler";

export default class TypesResource {
    private host: string;
    private endpoint: string = '/types';

    constructor(host: string) {
        this.host = host;
    }

    public async getAll() : Promise<TextRepoType[]> {
        const url = new URL(this.host + this.endpoint);
        const response = await fetch(url)
            .catch(await ErrorHandler.catch);
        await RestUtil.checkOk(url.toString(), response);
        return await response.json();
    }

    public async create(type: TextRepoType) {
        const url = this.host + this.endpoint;
        return await RestUtil.postResource(url, type);
    }

}
