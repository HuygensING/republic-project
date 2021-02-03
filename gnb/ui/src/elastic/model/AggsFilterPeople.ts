import {PersonType} from "./PersonType";

export default class AggsFilterPeople {
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
