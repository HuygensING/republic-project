import moment from "moment";
import Config from "../Config";

export function fromEsFormat(date: string): Date {
  return moment(date, Config.ES_DATE).toDate();
}
