import fetch from 'node-fetch';
import RestUtil from "../RestUtil";
import ErrorHandler from "../ErrorHandler";
export default class DocumentImagesResource {

    private host: string;
    private endpoint: string = '/documentimageset/{setId}/documentimages?skip=0';
    private authorization: string;

    constructor(host: string, authorization: string) {
        this.host = host;
        this.authorization = authorization;
    }

    public async getAll(setId: string) {
        let url = this.host + this.endpoint;
        url = url.replace('{setId}', setId);
        const response = await fetch(url, {headers: {'authorization': this.authorization}})
            .catch(await ErrorHandler.catch);
        await RestUtil.checkOk(url, response);
        return RestUtil.asJson(response);
    }
}
