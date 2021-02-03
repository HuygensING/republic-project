import moment from "moment";
import Config from "../../Config";

export default class AggsResolutionHistogram {
  public resolution_histogram: any;

  /**
   * @param begin date of first bucket
   * @param end date of last bucket
   * @param interval in days
   */
  constructor(begin: Date, end: Date, interval: number) {
    this.resolution_histogram = {
      "date_histogram": {
        "min_doc_count": 0,
        "field": "metadata.meeting.date",
        "fixed_interval": `${interval}d`,
        "extended_bounds": {
          "min": moment(begin).format(Config.ES_DATE),
          "max": moment(end).format(Config.ES_DATE)
        }
      },
      "aggs": {
        "resolution_ids": {
          "terms": { "field": "id" }
        }
      }
    };
  }
}
