import {PersonType} from "./PersonType";
import {AggsFilter} from "./AggsFilter";

export default class AggsFilterPersonType implements AggsFilter {
  public match: any;

  constructor(type: PersonType) {
    this.match = {"people.type": type};
  }
}
