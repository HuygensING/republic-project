import {Filter} from "./Filter";

export default class FilterIsMentioned implements Filter {
  public range: any;

  constructor() {
    this.range = {"mentionedCount": {"gte": 0}};
  }
}
