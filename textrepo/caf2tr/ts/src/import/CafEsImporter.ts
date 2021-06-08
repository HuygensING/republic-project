import {TextRepoImporter} from "./TextRepoImporter";
import TextRepoClient from "../client/textrepo/TextRepoClient";
import ImportResult from "./model/ImportResult";
import CafEsClient from "../client/caf/CafEsClient";
import * as fs from "fs";

/**
 * Delete a document by its externalId, including all its files, contents and metadata
 */
export default class CafEsImporter implements TextRepoImporter<string> {

  private textRepoClient: TextRepoClient;
  private cafEsClient: CafEsClient;
  private tmpDir: string;

  constructor(textRepoClient: TextRepoClient, cafEsClient: CafEsClient, tmpDir: string) {
    this.textRepoClient = textRepoClient;
    this.cafEsClient = cafEsClient;
    this.tmpDir = tmpDir;
  }

  public async run(): Promise<ImportResult<string>> {
    const docs = await this.cafEsClient.getAll();
    fs.writeFileSync(`${this.tmpDir}/docs.json`, JSON.stringify(docs))
    return new ImportResult<string>(docs.map(d => d.id), []);
  }
}
