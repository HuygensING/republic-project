import {Query} from "./Query";

export default class Request {

  public index: string;
  public body: Query;

  constructor(index: string, body: Query) {
    this.index = index;
    this.body = body;
  }
}
