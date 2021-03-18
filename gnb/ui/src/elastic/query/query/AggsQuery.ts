import {QueryWithSize} from "./QueryWithSize";
import {Agg} from "../aggs/Agg";

export class AggsQuery extends QueryWithSize {

  public aggs: any = {};

  constructor(agg: Agg) {
    super();
    this.size = 0;
    this.aggs[agg.name()] = agg.agg();
  }

}
