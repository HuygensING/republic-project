import Config from "./Config";
import TextRepoClient from "./client/textrepo/TextRepoClient";
import * as moment from 'moment'
import ErrorHandler from "./client/ErrorHandler";
import CafEsImporter from "./import/CafEsImporter";
import CafEsClient from "./client/caf/CafEsClient";
import TypeImporter from "./import/TypeImporter";

class Importer {

  private textRepoClient: TextRepoClient;
  private cafEsClient: CafEsClient;
  private command: string;

  private start: moment.Moment;
  private end: moment.Moment;
  private test = false;

  constructor() {
    this.textRepoClient = new TextRepoClient(Config.TR);
    this.cafEsClient = new CafEsClient(Config.CAF, Config.CAF_INDEX);
    this.command = process.argv.slice(2)[0];
  }

  public run() {
    console.log('Start Importer');
    switch (this.command) {
      case "create-all": {
        this.test = false;
        return this.createAll();
      }
      default: {
        console.error("Could not run importer. Expected command, but got:", this.command)
        break;
      }
    }

  }

  private async createAll() {
    this.start = moment();

    console.log('Creating types');
    const types = await new TypeImporter(this.textRepoClient).run()
    console.log(`Imported types: ${types.successes.length} successes and ${types.fails.length} failed`);
    let typeName = types.successes[0].name;

    console.log(`Creating caf files with type ${typeName}`);
    const result = await new CafEsImporter(
      this.textRepoClient,
      this.cafEsClient,
      Config.TMP,
      typeName
    ).run();
    console.log(`Imported caf files: ${result.successes.length} successes and ${result.fails.length} failed`);

    this.end = moment();
    let days = this.end.diff(this.start, 'days');
    let time = moment.utc(this.end.diff(this.start)).format("HH:mm:ss");
    console.log(`Took: ${days ? days + 'd' : ''} ${time}`);
  }

  public static async wait(ms) {
    return new Promise(resolve => {
      setTimeout(resolve, ms);
    });
  }
}

new Importer().run();
