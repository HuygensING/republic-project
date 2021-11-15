import Config from "./Config";
import TextRepoClient from "./client/textrepo/TextRepoClient";
import PimClient from "./client/pim/PimClient";
import TypeImporter from "./import/TypeImporter";
import ImportResult from "./import/model/ImportResult";
import CsvUtil from "./util/CsvUtil";
import CsvIdentifierRecord from "./import/model/CsvIdentifierRecord";
import * as moment from 'moment'
import TextRepoType from "./client/textrepo/model/TextRepoType";
import ErrorHandler from "./client/ErrorHandler";
import ExternalIdDeleter from "./import/ExternalIdDeleter";
import TaskImportImporter from "./import/TaskImportImporter";

class Importer {

  private textRepoClient: TextRepoClient;
  private pimClient: PimClient;
  private command: string;

  private start: moment.Moment;
  private end: moment.Moment;
  private test = false;

  constructor() {
    this.textRepoClient = new TextRepoClient(Config.TR);
    this.pimClient = new PimClient(Config.PIM, Config.GOOGLE_AUTHORIZATION);
    this.command = process.argv.slice(2)[0];
  }

  public run() {
    console.log('Start Importer');
    switch (this.command) {
      case "create-all": {
        this.test = false;
        return this.createAll();
      }
      case "test-create-all": {
        this.test = true;
        return this.createAll();
      }
      case "delete-all": {
        return this.deleteAll();
      }
      default: {
        console.error("Could not run importer. Expected command, but got:", this.command)
        break;
      }
    }

  }

  private async deleteAll(): Promise<ImportResult<string>> {
    return await new ExternalIdDeleter(
      this.textRepoClient,
      this.pimClient,
      await CsvUtil.getRecords<CsvIdentifierRecord>(Config.SUBSET_CSV)
    ).run();
  }


  private async createAll() {
    this.start = moment();
    const types = await new TypeImporter(this.textRepoClient).run()

    if (!types.isSuccesful()) {
      throw new Error('Could not create types');
    }

    console.log(`Create documents, files and versions for file types: ${JSON.stringify(types)}`);

    const records = await CsvUtil.getRecords<CsvIdentifierRecord>(Config.SUBSET_CSV);
    console.log(`Records to process: ${JSON.stringify(records.map(i => i.identifier))}`);
    records.filter(r => r)

    let recordCount = 0;
    for (const record of records) {
      console.log(`Import record ${++recordCount} of ${records.length}: ${record.identifier}`);
      try {
        await this.createByRecords(types.results, [record]);
      } catch (e) {
        ErrorHandler.handle(`Could not create record ${JSON.stringify(record)}`, e);
        await Importer.wait(5000);
      }
    }
    this.end = moment();
    const days = this.end.diff(this.start, 'days');
    let time = moment.utc(this.end.diff(this.start)).format("HH:mm:ss");
    console.log(`Created ${records.length} records in ${days ? days + 'd' : ''} ${time}`);
  }

  private async createByRecords(types: TextRepoType[], records: CsvIdentifierRecord[]) {

    let taskImporter = new TaskImportImporter(
      this.textRepoClient,
      this.pimClient,
      records,
      types
    );

    const imports = await taskImporter.run(this.test);

    console.log(`${records.length} records resulted in ${imports}`
      + ` imported versions (and their files and documents)`);
  }

  public static async wait(ms) {
    return new Promise(resolve => {
      setTimeout(resolve, ms);
    });
  }
}

new Importer().run();
