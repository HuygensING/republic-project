import {QueryWithSize} from "./QueryWithSize";

export class QueryWithIdsAndHighlights extends QueryWithSize {

  public aggs: any;
  private query: any;
  private highlight: any;
  constructor(ids: string[]) {
    super();
    this.size = 10000;

    this.query = {
      "ids": { "values": ids }
    };
    // TODO: add full-text highlighting
    this.highlight = {
      "fields": {
        "resolution.originalXml": {}
      }
    };

  }

}
