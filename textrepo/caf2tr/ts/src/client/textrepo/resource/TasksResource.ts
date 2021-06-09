import RestUtil from "../../RestUtil";
import FormData = require("form-data");

export default class TasksResource {

  private host: string;

  constructor(host: string) {
    this.host = host;
  }

  async import(typeName: string, externalId: string, contents: string, asLatestVersion: boolean): Promise<any> {
    const url = this.host + `/import/documents/${externalId}/${typeName}?allowNewDocument=true&asLatestVersion=${asLatestVersion}`;

    const formData = new FormData();
    formData.append('contents', contents, {filename: `${externalId}.${typeName}`});

    return await RestUtil.postFormData(url, formData);
  }
}
