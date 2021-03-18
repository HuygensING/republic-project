export default class SortAttendantCountDesc {
  public mentionedCount: any;

  constructor(order: string) {
    this.mentionedCount = {"order" : order};
  }
}
