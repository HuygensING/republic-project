import {Agg} from "./Agg";
import {Filter} from "../filter/Filter";

export default class AggWithFilters implements Agg {

  private readonly _name = 'filtered_aggs';
  private readonly _agg: any;

  constructor() {
    this._agg = {
      "filter": { "bool": { "filter": [] }},
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

  addFilter(filter: Filter) {
    this._agg.filter.bool.filter.push(filter);
  }

}
