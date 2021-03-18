import {Client} from "elasticsearch";
import {handleEsError} from "./EsErrorHandler";
import {ERR_ES_AGGREGATE_LOCATION} from "../content/Placeholder";
import FilterFunctionNamePrefix from "./query/filter/people/FilterFunctionNamePrefix";
import PeopleSearchParams from "./query/params/PeopleSearchParams";
import FilterFunctionCategory from "./query/filter/people/FilterFunctionCategory";
import AggAllFunctionCategories from "./query/aggs/people/AggAllFunctionCategories";
import AggsAllFunctions from "./query/aggs/people/AggsAllFunctions";
import PeopleAggsSearchParams from "./query/params/PeopleAggsSearchParams";

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
    const aggs = new AggsAllFunctions();
    aggs.addFilter(filter);
    const response = await this.request(aggs);
    return response.aggregations.nested_functions.filter_functions.function_id.buckets;
  }

  /**
   * Aggregate functions from gnb-resolutions by category
   */
  public async aggregateCategoriesBy(
    category: string
  ): Promise<any> {
    const filter = new FilterFunctionCategory(category);
    const aggs = new AggAllFunctionCategories();
    aggs.addFilter(filter);
    const response = await this.request(aggs);
    return response.aggregations.nested_functions.filter_functions.function_category.buckets;
  }

  private async aggregate(queryTemplate: any) {
    const params = new PeopleSearchParams(queryTemplate);
    return await this.esClient
      .search(params)
      .catch(e => handleEsError(e, ERR_ES_AGGREGATE_LOCATION));
  }

  private async request(aggs: AggAllFunctionCategories) {
    const params = new PeopleAggsSearchParams(aggs);
    return await this.esClient
      .search(params)
      .catch(e => handleEsError(e, ERR_ES_AGGREGATE_LOCATION));
  }
}
