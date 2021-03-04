import {Client} from "elasticsearch";
import {handleEsError} from "./EsErrorHandler";
import clone from "../util/clone";
import aggsAllFunctions from "./query/aggs/aggs-all-functions.json";
import {ERR_ES_AGGREGATE_LOCATION} from "../content/Placeholder";
import FilterFunctionNamePrefix from "./query/filter/FilterFunctionNamePrefix";
import PeopleRequest from "./query/aggs/PeopleRequest";

/**
 * ElasticSearch Resolution Resource
 */
export default class FunctionResource {

  private esClient: Client;
  private index: string;

  constructor(esClient: Client) {
    this.esClient = esClient;
    this.index = 'gnb-resolutions';
  }

  /**
   * Aggregate functions from gnb-resolutions by name prefix
   */
  public async aggregateBy(
    prefix: string
  ): Promise<any> {
    const query = clone<any>(aggsAllFunctions);

    const filters = query.nested_functions.aggs.filter_functions.filter.bool.must;
    filters.push(new FilterFunctionNamePrefix(prefix));

    const aggsRequest = new PeopleRequest(query);
    const response = await this.esClient
      .search(aggsRequest)
      .catch(e => handleEsError(e, ERR_ES_AGGREGATE_LOCATION));
    return response.aggregations.nested_functions.filter_functions.function_id.buckets;
  }
}
