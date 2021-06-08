import Config from "./Config";
import TextRepoClient from "./client/textrepo/TextRepoClient";
import * as moment from 'moment'
import ErrorHandler from "./client/ErrorHandler";
import CafEsImporter from "./import/CafEsImporter";
import CafEsClient from "./client/caf/CafEsClient";

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

    this.end = moment();
    const days = this.end.diff(this.start, 'days');
    let time = moment.utc(this.end.diff(this.start)).format("HH:mm:ss");
    const result = await new CafEsImporter(this.textRepoClient, this.cafEsClient, Config.TMP).run();
    console.log(`Imported ${result.successes.length} succesfull and ${result.fails.length} failed CAF docs in ${days ? days + 'd' : ''} ${time}`);
  }

  public static async wait(ms) {
    return new Promise(resolve => {
      setTimeout(resolve, ms);
    });
  }
}

new Importer().run();
