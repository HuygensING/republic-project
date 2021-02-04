import {Agg} from "./Agg";

export default class AggWithIdFilter implements Agg {

  private readonly _name = 'id_filtered_aggs';
  private readonly _agg: any;

  constructor(ids: string[]) {
    this._agg = {
      "filter": {
        "bool": {
          "should": [
            {
              "terms": {
                "_id": ids
              }
            }
          ]
        }
      },
      "aggs": {}
    }
  }

  agg(): any {
    return this._agg;
  }

  name(): string {
    return this._name;
  }

  addAgg(agg: Agg): void {
    this._agg.aggs[agg.name()] = agg.agg();
  }

}
