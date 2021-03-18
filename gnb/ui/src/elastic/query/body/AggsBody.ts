import {BodyWithSize} from "./BodyWithSize";
import {Agg} from "../aggs/Agg";

export default class AggsBody extends BodyWithSize {

  public aggs: any = {};

  constructor(agg: Agg) {
    super();
    this.size = 0;
    this.aggs[agg.name()] = agg.agg();
  }

}
