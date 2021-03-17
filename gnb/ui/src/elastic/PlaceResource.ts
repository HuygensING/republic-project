import {Client} from "elasticsearch";
import ResolutionRequest from "./query/aggs/ResolutionRequest";
import {handleEsError} from "./EsErrorHandler";
import {ERR_ES_AGGREGATE_LOCATION} from "../content/Placeholder";
import FilterAnnotationName from "./query/filter/FilterAnnotationName";
import FilterAnnotationValuePrefix from "./query/filter/FilterAnnotationValuePrefix";
import AggsAllAnnotations from "./query/aggs/AggsAllAnnotations";

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
   * Aggregate places from gnb-resolutions by name prefix
   */
  public async aggregateBy(
    prefix: string
  ): Promise<any> {
    const query = new AggsAllAnnotations();

    query.addFilter(new FilterAnnotationName('plaats'));
    query.addFilter(new FilterAnnotationValuePrefix(prefix));

    const response = await this.esClient
      .search(new ResolutionRequest(query))
      .catch(e => handleEsError(e, ERR_ES_AGGREGATE_LOCATION));

    return response.aggregations.nested_annotations.filter_annotations.sum.buckets;
  }
}
