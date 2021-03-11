import {Client} from "elasticsearch";
import {handleEsError} from "./EsErrorHandler";
import clone from "../util/clone";
import aggsAllFunctions from "./query/aggs/aggs-all-functions.json";
import aggsAllFunctionCategories from "./query/aggs/aggs-all-function-categories.json";
import {ERR_ES_AGGREGATE_LOCATION} from "../content/Placeholder";
import FilterFunctionNamePrefix from "./query/filter/FilterFunctionNamePrefix";
import PeopleAggsRequest from "./query/aggs/PeopleAggsRequest";
import FilterFunctionCategory from "./query/filter/FilterFunctionCategory";
import {Filter} from "./query/filter/Filter";

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
  public async aggregateByName(
    prefix: string
  ): Promise<any> {
    const filter = new FilterFunctionNamePrefix(prefix);
    const response = await this.aggregateByFilter(filter, aggsAllFunctions);
    return response.aggregations.nested_functions.filter_functions.function_id.buckets;
  }

  /**
   * Aggregate functions from gnb-resolutions by category
   */
  public async aggregateCategoriesBy(
    category: string
  ): Promise<any> {
    const filter = new FilterFunctionCategory(category);
    const response = await this.aggregateByFilter(filter, aggsAllFunctionCategories);
    return response.aggregations.nested_functions.filter_functions.function_category.buckets;
  }

  private async aggregateByFilter(filter: Filter, queryTemplate: any) {
    const query = clone<any>(queryTemplate);
    const filters = query.nested_functions.aggs.filter_functions.filter.bool.must;
    filters.push(filter);
    const aggsRequest = new PeopleAggsRequest(query);
    return await this.esClient
      .search(aggsRequest)
      .catch(e => handleEsError(e, ERR_ES_AGGREGATE_LOCATION));
  }
}
