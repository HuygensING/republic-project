import {QueryWithSize} from "../QueryWithSize";
import {isAgg} from "./Agg";

export class AggsQuery extends QueryWithSize {

  public aggs: any;

  constructor(aggs: any) {
    super();
    this.size = 0;

    if(isAgg(aggs)) {
      this.aggs = {};
      this.aggs[aggs.name()] = aggs.agg();
    } else {
      this.aggs = aggs;
    }
  }

}
