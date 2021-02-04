import {Filter} from "./Filter";

export default class FilterPersonName implements Filter {
  public prefix: any;

  constructor(prefix: string) {
    this.prefix = { "people.name": { "value": prefix }};
  }
}
