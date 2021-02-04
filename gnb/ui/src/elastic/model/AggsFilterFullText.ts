import {AggsFilter} from "./AggsFilter";

export default class AggsFilterFullText implements AggsFilter {
  public simple_query_string: any;

  constructor(simpleQuery: string) {
    this.simple_query_string = {
      "query": simpleQuery,
      "fields": ["resolution.plainText"],
      "default_operator": "and"
    };
  }
}
