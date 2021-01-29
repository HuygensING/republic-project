import {PersonType} from "./PersonType";

export default class AggsFilterPersonType {
  public match: any;

  constructor(type: PersonType) {
    this.match = {"people.type": type};
  }
}
