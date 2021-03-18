import {Filter} from "../Filter";

export default class FilterPeople implements Filter {
  public nested: any;

  constructor(people: number[]) {
    this.nested = {
      "path": "people",
      "query": {
        "bool": {"must": [{"terms": {"people.id": people}}]}
      }
    };
  }
}
