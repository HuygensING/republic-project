import {Query} from "./query/Query";

/**
 * Pass an instance of (a subclass of) SearchParams to the es client.
 */
export default class SearchParams {

  public index: string;
  public body: Query;

  constructor(index: string, body: Query) {
    this.index = index;
    this.body = body;
  }
}
