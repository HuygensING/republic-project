import moment from "moment";
import Config from "../Config";

export function toEsFormat(date: Date): string {
  return moment(date).format(Config.ES_DATE);
}
