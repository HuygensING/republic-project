import {Client} from "elasticsearch";
import {handleEsError} from "../EsErrorHandler";
import {ERR_ES_AGGREGATE_LOCATION} from "../../content/Placeholder";
import FilterFunctionNamePrefix from "../query/filter/people/FilterFunctionNamePrefix";
import FilterFunctionCategory from "../query/filter/people/FilterFunctionCategory";
import AggAllFunctionCategories from "../query/aggs/people/AggAllFunctionCategories";
import PeopleSearchParams from "../query/search-params/PeopleSearchParams";
import PeopleAggsSearchParams from "../query/search-params/PeopleAggsSearchParams";
import AggAllFunctions from "../query/aggs/people/AggAllFunctions";

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
    const aggs = new AggAllFunctions();
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
