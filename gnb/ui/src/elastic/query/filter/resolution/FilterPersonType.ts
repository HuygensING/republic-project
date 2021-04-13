import {PersonType} from "../../../model/PersonType";
import {Filter} from "../Filter";

export default class FilterPersonType implements Filter {
  public match: any;

  constructor(type: PersonType) {
    this.match = {"people.type": type};
  }
}
