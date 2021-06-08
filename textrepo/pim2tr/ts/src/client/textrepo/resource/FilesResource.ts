import fetch from 'node-fetch';
import RestUtil from "../../RestUtil";
import TextRepoType from "../model/TextRepoType";
import TextRepoFile from "../model/TextRepoFile";
import ErrorHandler from "../../ErrorHandler";

export default class FilesResource {
    private host: string;
    private endpoint: string = '/files';
    private fileEndpoint: string = '/files/{id}';

    constructor(host: string) {
        this.host = host;
    }

    public async delete(fileId: string) : Promise<boolean> {
        const url = this.host + this.fileEndpoint
            .replace('{id}', fileId);
        let response = await RestUtil.delete(url, {});
        return response.status ==  200;
    }

}
