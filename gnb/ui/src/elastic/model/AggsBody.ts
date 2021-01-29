import {EsBody} from "./EsBody";

export class AggsBody extends EsBody {

  public aggs: any;

  constructor(aggs: any) {
    super();
    this.size = 0;
    this.aggs = aggs;
  }

}
