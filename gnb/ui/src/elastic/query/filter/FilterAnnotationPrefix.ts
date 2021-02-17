import {PersonType} from "../../model/PersonType";
import {Filter} from "./Filter";

export default class FilterAnnotation implements Filter {
  public nested: any;

  constructor(name: string, value: string) {
    this.nested = {
      "path": "annotations",
      "query": {
        "bool": {
          "must": [
            {"match": {"annotations.name": name}},
            {"prefix": { "annotations.value": { "value": value }}}
          ]
        }
      }
    };
  }
}
