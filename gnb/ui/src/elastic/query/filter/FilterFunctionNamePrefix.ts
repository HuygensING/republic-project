import {Filter} from "./Filter";

export default class FilterFunctionNamePrefix implements Filter {
  public prefix: any;

  constructor(prefix: string) {
    this.prefix = { "functions.name": { "value": prefix }};
  }
}
