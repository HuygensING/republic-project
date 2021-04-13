import fetch from 'node-fetch';
import RestUtil from "../../RestUtil";
import TextRepoFile from "../model/TextRepoFile";

export default class DocumentFilesResource {
    private host: string;
    private endpoint: string = '/documents/{id}/files';

    constructor(host: string) {
        this.host = host;
    }

    public async getAll(docId) : Promise<TextRepoFile[]> {
        const url = new URL(this.host + this.endpoint.replace('{id}', docId));
        const response = await fetch(url);
        await RestUtil.checkOk(url.toString(), response);
        let page = await response.json();
        return page.items;
    }

}
