import Config from "./Config";
import TextRepoClient from "./client/textrepo/TextRepoClient";
import * as moment from 'moment'
import ErrorHandler from "./client/ErrorHandler";

class Importer {

  private textRepoClient: TextRepoClient;
  private command: string;

  private start: moment.Moment;
  private end: moment.Moment;
  private test = false;

  constructor() {
    this.textRepoClient = new TextRepoClient(Config.TR);
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

    let recordCount = 0;
    let records = [];
    for (const record of records) {
      try {
        console.log(`Import record ${++recordCount} of ${records.length}: ${record.identifier}`);

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

  public static async wait(ms) {
    return new Promise(resolve => {
      setTimeout(resolve, ms);
    });
  }
}

new Importer().run();
