import TextRepoDocument from "../model/TextRepoDocument";
import fetch from 'node-fetch';
import RestUtil from "../../RestUtil";
import ErrorHandler from "../../ErrorHandler";

type DocumentCollectionParams = {
    externalId: string
    createdAfter: string;
    offset: number;
    size: number;
};

export default class DocumentsResource {

    private host: string;
    private endpoint: string = '/documents';
    private docEndpoint: string = '/documents/{id}';

    constructor(host: string) {
        this.host = host;
    }

    public async getAll(params: Partial<DocumentCollectionParams>) {
        const url = new URL(this.host + this.endpoint);
        Object.keys(params).forEach(p => url.searchParams.append(p, params[p]))
        const response = await fetch(url);
        await RestUtil.checkOk(url.toString(), response);
        return response.json();
    }

    public async delete(docId: string) : Promise<boolean> {
        const url = this.host + this.docEndpoint
            .replace('{id}', docId);
        let response = await RestUtil.delete(url, {});
        return response.status ==  200;
    }

    public async getByExternalId(externalId: string) : Promise<TextRepoDocument> {
        let page = await this.getAll({externalId});
        if(page.items.length !== 1) {
            return null;
        }
        return page.items[0];
    }
}
