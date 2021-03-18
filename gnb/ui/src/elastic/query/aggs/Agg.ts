/**
 * Building block of Elasticsearch aggregations
 */
export interface Agg {

  name(): string;

  agg(): any;

  /**
   * Add agg to $.aggs
   */
  addAgg(agg: Agg): void;

}
