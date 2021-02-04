export interface Agg {

  name(): string;

  agg(): any;

  /**
   * Add agg to $.aggs
   */
  addAgg(agg: Agg): void;

}

/**
 * Agg type guard
 */
export function isAgg(obj: any): obj is Agg {
  return (obj as Agg).name !== undefined
    && (obj as Agg).agg !== undefined;
}
