import {Filter} from "./Filter";

export default class FilterFunctionNamePrefix implements Filter {
  public prefix: any;

  constructor(category: string) {
    this.prefix = {"functions.category": {"value": category}};
  }
}
