import moment from "moment";
import Config from "../../../../Config";
import {Agg} from "../Agg";

export default class AggResolutionHistogram implements Agg {

  private _name = 'resolution_histogram';
  private _agg: any;

  /**
   * @param begin date of first bucket
   * @param end date of last bucket
   * @param interval in days
   */
  constructor(begin: Date, end: Date, interval: number) {
    this._agg = {
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
          "terms": {
            "field": "id",
            "size": 10000
          }
        }
      }
    };
  }

  addAgg(agg: Agg): void {
    this._agg.aggs[agg.name()] = agg.agg()
  }

  agg(): any {
    return this._agg;
  }

  name(): string {
    return this._name;
  }
}
