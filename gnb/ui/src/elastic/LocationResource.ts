import {Client} from "elasticsearch";
import AggsRequest from "./query/aggs/AggsRequest";
import {handleEsError} from "./EsErrorHandler";
import clone from "../util/clone";
import aggsAllAnnotations from "./query/aggs/aggs-all-annotations.json";
import {ERR_ES_AGGREGATE_LOCATION} from "../Placeholder";
import FilterAnnotationName from "./query/filter/FilterAnnotationName";
import FilterAnnotationValue from "./query/filter/FilterAnnotationValue";

/**
 * ElasticSearch Resolution Resource
 */
export default class ResolutionResource {

  private esClient: Client;
  private index: string;

  constructor(esClient: Client) {
    this.esClient = esClient;
    this.index = 'gnb-resolutions';
  }

  /**
   * Aggregate locations from gnb-resolutions by name prefix
   */
  public async aggregateBy(
    prefix: string
  ): Promise<any> {
    const query = clone<any>(aggsAllAnnotations);

    const filters = query.nested_annotations.aggs.filter_annotations.filter.bool.must;
    filters.push(new FilterAnnotationName('plaats'));
    filters.push(new FilterAnnotationValue(prefix));

    const response = await this.esClient
      .search(new AggsRequest(query))
      .catch(e => handleEsError(e, ERR_ES_AGGREGATE_LOCATION));

    return response.aggregations.people.filter_people.sum_people_id.buckets;
  }



}
