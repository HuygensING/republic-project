import fetch from "node-fetch";
import ErrorHandler from "../ErrorHandler";
import RestUtil from "../RestUtil";
import DocumentImageTranscriptionsResource from "./DocumentImageTranscriptionsResource";

export class DocumentImageTranscriptionsResourceImpl implements DocumentImageTranscriptionsResource {

    private host: string;
    private endpoint: string = '/documentimage/{imageId}/transcriptions';
    private authorization: string;

    constructor(host: string, authorization: string) {
        this.host = host;
        this.authorization = authorization;
    }

    public async getAll(imageId: string) {
        let url = this.host + this.endpoint;
        url = url.replace('{imageId}', imageId);
        try {
            const response = await fetch(url, {headers: {'authorization': this.authorization}});
            await RestUtil.checkOk(url, response);
            return RestUtil.asJson(response);
        } catch (e) {
            console.log(Date.now(), 'Retry in 2s after error: ', JSON.stringify(e));
            await RestUtil.wait(2000);
            return this.getAll(imageId);
        }
    }

}
