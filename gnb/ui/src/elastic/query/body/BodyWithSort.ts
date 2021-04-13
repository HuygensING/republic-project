import {BodyWithSize} from "./BodyWithSize";
import {Filter} from "../filter/Filter";
import {Sort} from "../sort/Sort";

export class BodyWithSort extends BodyWithSize {

  private query: any;
  private sort: any[];

  constructor() {
    super();
    this.size = 10000;

    this.sort = [];
    this.query = {
      "bool": {
        "must": []
      }
    };

  }

  addFilter(filter: Filter) {
    this.query.bool.must.push(filter);
  }

  addSort(sort: Sort) {
    this.sort.push(sort);
  }

}
