export default class SortAttendantCount {
  public attendantCount: any;

  constructor(order: string) {
    this.attendantCount = {"order" : order};
  }
}
