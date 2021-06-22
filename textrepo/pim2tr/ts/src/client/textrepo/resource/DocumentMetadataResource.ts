import RestUtil from "../../RestUtil";

export default class DocumentMetadataResource {
    private host: string;
    private endpoint: string = '/documents/{id}/metadata/{key}';

    constructor(host: string) {
        this.host = host;
    }

    public async create(id: string, key: string, value: string) {
        const url = this.host + this.endpoint
            .replace('{id}', id)
            .replace('{key}', key);
        return await RestUtil.put(url, value, 'text/plain');
    }

}
