import moment from "moment";
import Config from "../../../../Config";
import {Filter} from "../Filter";

export default class FilterRange implements Filter {
  public range: any;

  constructor(begin: Date, end: Date) {
    this.range = {
      "metadata.meeting.date": {
        "gte": moment(begin).format(Config.ES_DATE),
        "lte": moment(end).format(Config.ES_DATE)
      }
    };
  }
}
