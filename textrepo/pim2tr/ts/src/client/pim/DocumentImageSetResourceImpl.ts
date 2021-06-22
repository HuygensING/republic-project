import fetch from 'node-fetch';
import RestUtil from "../RestUtil";
import {DocumentImageSetResource} from "./DocumentImageSetResource";
import ErrorHandler from "../ErrorHandler";

export default class DocumentImageSetResourceImpl implements DocumentImageSetResource {

    private host: string;
    private endpoint: string = '/documentimageset';
    private authorization: string;

    constructor(host: string, authorization: string) {
        this.host = host;
        this.authorization = authorization;
    }

    public async getAll() {
        let url = this.host + this.endpoint;
        const response = await fetch(url, {headers: {'authorization': this.authorization}});
        await RestUtil.checkOk(url, response);
        return RestUtil.asJson(response);
    }
}
