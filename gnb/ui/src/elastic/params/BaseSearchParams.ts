import {Query} from "../query/query/Query";

export default class BaseSearchParams {

  public index: string;
  public body: Query;

  constructor(index: string, body: Query) {
    this.index = index;
    this.body = body;
  }
}
