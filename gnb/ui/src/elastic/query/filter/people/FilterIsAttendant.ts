import {Filter} from "../Filter";

export default class FilterIsAttendant implements Filter {
  public range: any;

  constructor() {
    this.range = {"attendantCount" : { "gte": 0 }};
  }
}
