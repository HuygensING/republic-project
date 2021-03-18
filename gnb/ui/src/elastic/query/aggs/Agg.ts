/**
 * Building block of Elasticsearch Aggs
 */
export interface Agg {

  name(): string;

  agg(): any;

  /**
   * Add agg to $.aggs
   */
  addAgg(agg: Agg): void;

}
