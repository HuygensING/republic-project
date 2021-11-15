import * as moment from 'moment'
import XmlResolutionConverter from "./convert/XmlResolutionConverter";
import Config from "./Config";
import ConvertResult from "./convert/ConvertResult";
import * as glob from 'glob';
import ErrorHandler from "./ErrorHandler";
import EsService from "./convert/EsService";
import MysqlService from "./convert/MysqlService";
import PersonConverter from "./convert/MysqlPersonConverter";
import {PersonPresenceAgg} from "./PersonPresenceAgg";
import {aggregatePeople} from "./convert/AggregatePeopleUtil";

class Converter {

  private command: string;

  private start: moment.Moment;
  private end: moment.Moment;
  private esService = new EsService();
  private personConverter: PersonConverter;
  private mysqlService: MysqlService;
  private peopleAgg: PersonPresenceAgg[] = [];

  public async run() {
    console.log('Start Importer');

    await this.init();

    switch (this.command) {
      case "convert": {
        await this.convertXml();
        await this.convertDb();
        break;
      }
      default: {
        console.error("Could not run converter. Expected command, but got:", this.command)
        break;
      }
    }

    this.close();

  }

  private close() {
    this.mysqlService.close();
  }

  private async init() {
    this.command = process.argv.slice(2)[0];
    this.mysqlService = new MysqlService();
    await this.mysqlService.connect();
    let functionRows = await this.mysqlService.getAllFunctions();
    this.personConverter = new PersonConverter(functionRows);
  }

  private async convertXml() {
    this.logStart('converting xml');

    const xmlGlob = `${Config.XML_GLOB}`;
    const files = glob.sync(xmlGlob, {nodir: true});
    const result = new ConvertResult<string>();
    result.success = true;
    let counter = 0;
    for (const file of files) {
      console.log(`Coverting file ${++counter} of ${files.length}: ${file}`);
      await this.convertFile(file, result);
    }
    this.logEnd(result);
  }

  private async convertFile(file, result: ConvertResult<string>) {
    try {
      const esDocs = await XmlResolutionConverter.convert(file);
      await aggregatePeople(this.peopleAgg, esDocs);
      for (const esDoc of esDocs) {
        await this.esService.createEsDoc(Config.RESOLUTION_INDEX, esDoc);
      }
    } catch (error) {
      ErrorHandler.handle(`Failed to convert ${file}`, error);
      result.success = false;
      result.failed.push(file);
    }
    result.results.push(file);
  }

  private async convertDb() {
    this.logStart("converting database");

    if(!this.peopleAgg.length) {
      throw Error('peopleAgg empty');
    }
    this.personConverter.setPeopleAgg(this.peopleAgg)

    try {
      const dbPeople = await this.mysqlService.getAllPeople();
      const results = new ConvertResult<string>();
      results.success = true;
      let counter = 0;
      for (const row of dbPeople) {
        console.log(`converting person ${++counter} of ${dbPeople.length}: ${row['Id_persoon']}`);
        await this.convertRow(row, results);
      }
      this.logEnd(results);
    } catch (err) {
      ErrorHandler.handle('could not convert db', err);
    }
  }

  /**
   * Convert row and add new document to es index
   * Update results afterwards
   */
  private async convertRow(row, results: ConvertResult<string>) {
    try {
      const result = await this.personConverter.convert(row);
      await this.esService.createEsDoc(Config.PERSON_INDEX, result);
      results.results.push(result.id);
    } catch (err) {
      ErrorHandler.handle(`Could not process person ${row['Id_persoon']}`, err);
      results.success = false;
      results.failed.push(row['Id_persoon'])
    }
  }

  private logStart(activity: string) {
    this.start = moment();
    console.log(`Start ${activity}`);
  }

  private logEnd(result: ConvertResult<string>) {
    this.end = moment();
    const days = this.end.diff(this.start, 'days');
    let time = moment.utc(this.end.diff(this.start)).format("HH:mm:ss");
    console.log(`Finished conversion of ${result.results.length} records in ${days ? days + 'd' : ''} ${time}`);
    if (!result.isSuccess) {
      ErrorHandler.print(`Conversion of ${result.failed.length} records failed:\n${JSON.stringify(result.failed)}`);
    }
  }

}

new Converter().run();
