import {QueryWithSize} from "./QueryWithSize";
import {Filter} from "../filter/Filter";
import {Sort} from "../sort/Sort";

export class QueryWithSort extends QueryWithSize {

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
