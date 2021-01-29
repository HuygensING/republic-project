import moment from "moment";
import Config from "../../Config";

export default class AggsFilterRange {
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
