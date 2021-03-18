import {Body} from "./body/Body";

/**
 * Pass an instance of (a subclass of) SearchParams to the es client.
 * Structure:
 * - A SearchParams-instance has a body
 * - Bodies can have a query, highlight query and aggregations
 * - Queries and aggregations can be filtered and sorted
 */
export default class SearchParams {

  public index: string;
  public body: Body;

  constructor(index: string, body: Body) {
    this.index = index;
    this.body = body;
  }
}
