export default class AggsFilterPersonName {
  public prefix: any;

  constructor(prefix: string) {
    this.prefix = { "people.name": { "value": prefix }};
  }
}
