import {TextRepoImporter} from "./TextRepoImporter";
import TextRepoClient from "../client/textrepo/TextRepoClient";
import ImportResult from "./model/ImportResult";
import CafEsClient from "../client/caf/CafEsClient";
import {CafDoc} from "./model/CafDoc";
import ErrorHandler from "../client/ErrorHandler";

/**
 * Delete a document by its externalId, including all its files, contents and metadata
 */
export default class CafEsImporter implements TextRepoImporter<string> {

  private textRepoClient: TextRepoClient;
  private cafEsClient: CafEsClient;
  private tmpDir: string;
  private typeName: string;

  constructor(
    textRepoClient: TextRepoClient,
    cafEsClient: CafEsClient,
    tmpDir: string,
    typeName: string
  ) {
    this.textRepoClient = textRepoClient;
    this.cafEsClient = cafEsClient;
    this.tmpDir = tmpDir;
    this.typeName = typeName;
  }

  public async run(): Promise<ImportResult<string>> {
    const results: string[] = [];
    const failed: string[] = [];

    await this.cafEsClient.handleAll(async (doc: CafDoc) => {
      try {
        console.log(`Importing externalId ${doc.metadata.id} and type ${this.typeName}`);
        await this.textRepoClient.tasks.import(this.typeName, doc.metadata.id, JSON.stringify(doc), true);
        results.push(doc.metadata.id);
      } catch (e) {
        failed.push(doc.metadata.id);
        ErrorHandler.handle('Could not import document', e);
      }
    });

    return new ImportResult<string>(results, failed);
  }
}
