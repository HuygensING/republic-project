import * as fs from "fs";
import * as xmldom from "xmldom"
import * as moment from "moment";
import Config from "../Config";

export default class TimeUtil {
  public static getNow(): string {
    return moment(moment.now()).format();
  }

  public static getFormatted(dateInput: moment.MomentInput): string {
    return moment(dateInput).format(Config.DATE_FORMAT)
  }
}
