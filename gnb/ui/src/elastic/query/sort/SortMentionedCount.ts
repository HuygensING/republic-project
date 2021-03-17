export default class SortAttendantCountDesc {
  public attendantCount: any;

  constructor(order: string) {
    this.attendantCount = {"order" : order};
  }
}
