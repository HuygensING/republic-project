import {Filter} from "../Filter";
import {PersonType} from "../../../model/PersonType";

export default class FilterPeople implements Filter {
  public nested: any;

  constructor(people: number[], type?: PersonType) {
    this.nested = {
      "path": "people",
      "query": {
        "bool": {"must": [
          {"terms": {"people.id": people}}
        ]}
      }
    };
    if(type) {
      this.nested.query.bool.must.push({"match": {"people.type": type}});
    }
  }

}
