import {Sort} from "./Sort";

export default class SortAttendantCountDesc implements Sort {
  public mentionedCount: any;

  constructor(order: string) {
    this.mentionedCount = {"order" : order};
  }
}
