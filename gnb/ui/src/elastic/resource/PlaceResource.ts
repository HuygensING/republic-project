import {Client} from "elasticsearch";
import {handleEsError} from "../EsErrorHandler";
import {ERR_ES_AGGREGATE_LOCATION} from "../../content/Placeholder";
import FilterAnnotationName from "../query/filter/resolution/FilterAnnotationName";
import FilterAnnotationValuePrefix from "../query/filter/resolution/FilterAnnotationValuePrefix";
import AggAllAnnotations from "../query/aggs/resolution/AggAllAnnotations";
import ResolutionAggsSearchParams from "../query/search-params/ResolutionAggsSearchParams";

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

    const query = new AggAllAnnotations();
    query.addFilter(new FilterAnnotationName('plaats'));
    query.addFilter(new FilterAnnotationValuePrefix(prefix));
    const params = new ResolutionAggsSearchParams(query);

    const response = await this.esClient
      .search(params)
      .catch(e => handleEsError(e, ERR_ES_AGGREGATE_LOCATION));

    return response.aggregations.nested_annotations.filter_annotations.sum.buckets;
  }
}
