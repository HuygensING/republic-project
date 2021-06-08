import RestUtil from "../../RestUtil";
import FormData = require("form-data");

export default class TasksResource {

  private host: string;
  private endpoint: string = '/delete/documents/{externalId}';

  constructor(host: string) {
    this.host = host;
  }

  public async deleteDocFilesContentsBy(externalId: string): Promise<boolean> {
    const url = this.host + this.endpoint
      .replace('{externalId}', externalId);
    const result = await RestUtil.delete(url, {accept: 'application/json'});
    return result.status == 200;
  }

  async import(typeName: string, externalId: string, contents: string, asLatestVersion: boolean): Promise<any> {
    const url = this.host + `/import/documents/${externalId}/${typeName}?allowNewDocument=true&asLatestVersion=${asLatestVersion}`;


    const formData = new FormData();
    formData.append('contents', contents, {filename: `${externalId}-${typeName}.xml`});

    return await RestUtil.postFormData(url, formData);
  }
}
