import {Sort} from "./Sort";

export default class SortAttendantCount implements Sort {
  public attendantCount: any;

  constructor(order: string) {
    this.attendantCount = {"order" : order};
  }
}
