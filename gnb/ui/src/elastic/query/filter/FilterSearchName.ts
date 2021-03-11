import {Filter} from "./Filter";

export default class FilterSearchName implements Filter {
  public prefix: any;

  constructor(prefix: string) {
    this.prefix = { "searchName": { "value": prefix }};
  }
}
