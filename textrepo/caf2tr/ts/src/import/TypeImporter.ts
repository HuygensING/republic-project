import {TextRepoImporter} from "./TextRepoImporter";
import Config from "../Config";
import TextRepoType from "../client/textrepo/model/TextRepoType";
import TextRepoClient from "../client/textrepo/TextRepoClient";
import ImportResult from "./model/ImportResult";
import ErrorHandler from "../client/ErrorHandler";
import RequestError from "../client/RequestError";
import CsvUtil from "../util/CsvUtil";
import CsvTypeRecord from "./model/CsvTypeRecord";

export default class TypeImporter implements TextRepoImporter<TextRepoType> {
  private textRepoClient: TextRepoClient;

  private typeWithNameExists = new RegExp('.*Duplicate type name:.*');

  constructor(textRepoClient: TextRepoClient) {
    this.textRepoClient = textRepoClient;
  }

  public async run(): Promise<ImportResult<TextRepoType>> {
    const records: CsvTypeRecord[] = await CsvUtil.getRecords<CsvTypeRecord>(Config.TYPE_CSV);
    console.log('Create types: ', JSON.stringify(records));
    let created: TextRepoType[] = [];
    let failed: TextRepoType[] = [];
    for (const record of records) {
      let typeImportResult = await this.createType(record.name, record.mimetype);
      failed.push(...typeImportResult.fails);
      created.push(...typeImportResult.successes);
    }
    return new ImportResult<TextRepoType>(created, failed);
  }

  private async createType(name, mimetype): Promise<ImportResult<TextRepoType>> {
    const result = new TextRepoType(name, mimetype);
    try {
      const newType = await this.textRepoClient.types.create(new TextRepoType(name, mimetype))
      console.log(`Created type ${newType.id} with name ${name} and mimetype ${mimetype}`);
      return new ImportResult<TextRepoType>([newType], []);
    } catch (e) {
      if (e instanceof RequestError && this.typeWithNameExists.test(e.responseBody)) {
        const existingType = (await this.textRepoClient.types.getAll()).find(t => t.name == name);
        console.log(`Type exists with name ${name}: ${existingType.id}`);
        return new ImportResult<TextRepoType>([existingType], []);
      }
      ErrorHandler.handle(`Could not create type ${name} with mimetype ${mimetype}`, e);
      return new ImportResult<TextRepoType>([], [result]);
    }
  }
}
