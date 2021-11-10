import EsPersonDocument from "../model/person/EsPersonDocument";
import {PersonFunction} from "../model/person/PersonFunction";
import {Metadata} from "../model/person/Metadata";
import TimeUtil from "./TimeUtil";
import {PersonPresenceAgg} from "../PersonPresenceAgg";
import {toName} from "./NameUtil";

export default class MysqlPersonConverter {

  private personMapping = {
    familyName: "geslachtsnaam",
    firstNames: "voornamen",
    prepositions: "preposities",
    interpositions: "intraposities",
    postpositions: "postposities",
    nameType: "naamstype",
    quality: "karakteristiek",
    category: "cats"
  };

  private functionRows: any[];
  private peopleAgg: PersonPresenceAgg[];

  constructor(functionRows: any[]) {
    this.functionRows = functionRows;
  }

  public convert(personRow: any): EsPersonDocument {
    const result = new EsPersonDocument(personRow['Id_persoon'], new Metadata(TimeUtil.getNow()));

    this.setAggCounts(result);

    Object.keys(this.personMapping).forEach(key => {
      let value = personRow[this.personMapping[key]];
      result[key] = value ? value : undefined;
    });
    result.searchName = toName(result);

    result.functions = [];
    this.functionRows
      .filter(r => r.persoon === result.id)
      .forEach(f => MysqlPersonConverter.createFunction(f, result));

    return result;
  }

  private setAggCounts(result: EsPersonDocument) {
    let agg = this.peopleAgg.find(a => ('' + a.id) === '' + result.id);
    if (!agg) {
      console.warn(`Could not find agg for ${result.id} in ${this.peopleAgg.map(a => a.id)}`);
    } else {
      result.mentionedCount = agg.mentioned;
      result.attendantCount = agg.attended;
    }
  }

  private static createFunction(f, result) {
    console.log(`found function ${f.naamId} for person ${f.persoon}`);
    const functionResult = new PersonFunction(f.naamId);
    functionResult.name = f.naam ? f.naam : undefined;
    functionResult.start = MysqlPersonConverter.createDate(f.beginJaar, f.beginMaand, f.beginDag);
    functionResult.end = MysqlPersonConverter.createDate(f.eindJaar, f.eindMaand, f.eindDag);
    functionResult.category = f.functietype;
    result.functions.push(functionResult);
  }

  private static createDate(year: number, month: number, day: number): string {
    if (year === 0) {
      return undefined;
    }
    const dateInput = {};
    dateInput['year'] = year;
    if (month !== 0) {
      dateInput['month'] = month;
    }
    if (day !== 0) {
      dateInput['D'] = day;
    }
    return TimeUtil.getFormatted(dateInput);
  }

  setPeopleAgg(peopleAgg: PersonPresenceAgg[]) {
    this.peopleAgg = peopleAgg;
  }
}
