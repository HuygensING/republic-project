import {AggImpl} from "./AggImpl";
import {Filter} from "../filter/Filter";

export default class AggsAllAnnotations extends AggImpl {

  constructor() {
    super('nested_annotations')
    this._agg = {
      "nested": {
        "path": "annotations"
      },
      "aggs": {
        "filter_annotations": {
          "filter": {
            "bool": {
              "must": []
            }
          },
          "aggs": {
            "sum": {
              "terms": {
                "field": "annotations.value.keyword",
                "size": 10
              }
            }
          }
        }
      }
    };
  }
  addFilter(filter: Filter) {
    this._agg.aggs.filter_annotations.filter.bool.must.push(filter);
  }

}
