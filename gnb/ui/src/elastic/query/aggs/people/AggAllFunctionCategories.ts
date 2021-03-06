import {AggImpl} from "../AggImpl";
import {Filter} from "../../filter/Filter";

export default class AggAllFunctionCategories extends AggImpl {

  constructor() {
    super('nested_functions')
    this._agg = {
        "nested": {
          "path": "functions"
        },
        "aggs": {
          "filter_functions": {
            "filter": {
              "bool": {
                "must": []
              }
            },
            "aggs": {
              "function_category": {
                "terms": {
                  "field": "functions.category",
                  "size": 10000
                },
                "aggs": {
                  "unnest_functions": {
                    "reverse_nested": {},
                    "aggs": {
                      "people": {
                        "terms": {
                          "field": "id",
                          "size": 10000
                        }
                      }
                    }
                  }
                }
              }
            }
          }
        }
      };
  }
  addFilter(filter: Filter) {
    this._agg.aggs.filter_functions.filter.bool.must.push(filter);
  }

}
