import {Filter} from "../Filter";

export default class FilterFullText implements Filter {
  public simple_query_string: any;

  constructor(simpleQuery: string) {
    this.simple_query_string = {
      "query": simpleQuery,
      "fields": ["resolution.plainText"],
      "default_operator": "and"
    };
  }
}
