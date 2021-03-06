import {BodyWithIds} from "./BodyWithIds";

export class BodyWithIdsAndHighlights extends BodyWithIds {

  private highlight: any;

  /**
   * Find resolutions, and highlight terms with .highlight
   *
   * @param ids resolution IDs
   * @param highlight using simple query format
   */
  constructor(ids: string[], highlight: string) {
    super(ids);

    this.highlight = highlight ? {
      "number_of_fragments": 0,
      "pre_tags" : ['<span class="highlight">'],
      "post_tags" : ['</span>'],
      "fields": {
        "resolution.originalXml": {
          "highlight_query": {
            "simple_query_string" : {
              "query": highlight,
              "fields": ["resolution.originalXml"],
              "default_operator": "and"
            }
          }
        }
      }
    } : undefined;

  }

}
