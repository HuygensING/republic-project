import {Sort} from "./Sort";

export default class SortMentionedCount implements Sort {
  public mentionedCount: any;

  constructor(order: string) {
    this.mentionedCount = {"order" : order};
  }
}
