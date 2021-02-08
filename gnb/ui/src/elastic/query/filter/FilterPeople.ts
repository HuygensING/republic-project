import {PersonType} from "../../model/PersonType";
import {Filter} from "./Filter";

export default class FilterPeople implements Filter {
  public nested: any;

  constructor(id: number, type: PersonType) {
    this.nested = {
      "path": "people",
      "query": {
        "bool": {
          "must": [
            {"match": {"people.id": id}},
            {"match": {"people.type": type}}
          ]
        }
      }
    };
  }
}
