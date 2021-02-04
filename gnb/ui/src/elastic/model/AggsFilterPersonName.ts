import {AggsFilter} from "./AggsFilter";

export default class AggsFilterPersonName implements AggsFilter {
  public prefix: any;

  constructor(prefix: string) {
    this.prefix = { "people.name": { "value": prefix }};
  }
}
