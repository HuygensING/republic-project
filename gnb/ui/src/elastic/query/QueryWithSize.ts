import {Query} from "./Query";

export class QueryWithSize implements Query {
  public size: number;

  constructor() {
    this.size = 10;
  }
}
