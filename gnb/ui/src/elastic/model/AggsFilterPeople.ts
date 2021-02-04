import {PersonType} from "./PersonType";
import {AggsFilter} from "./AggsFilter";

export default class AggsFilterPeople implements AggsFilter {
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
