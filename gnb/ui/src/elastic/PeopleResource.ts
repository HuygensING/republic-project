import {Client, MGetResponse} from "elasticsearch";
import AggsRequest from "./query/aggs/AggsRequest";
import aggsPeopleWithName from './query/aggs/aggs-people-with-filters.json';
import FilterPersonName from "./query/filter/FilterPersonName";
import {Person} from "./model/Person";
import {PersonType} from "./model/PersonType";
import FilterPersonType from "./query/filter/FilterPersonType";
import {ERR_ES_AGGREGATE_PEOPLE, ERR_ES_GET_MULTI_PEOPLE} from "../Placeholder";
import {handleEsError} from "./EsErrorHandler";

/**
 * ElasticSearch Resolution Resource
 */
export default class PeopleResource {

  private esClient: Client;
  private index: string;

  constructor(esClient: Client) {
    this.esClient = esClient;
    this.index = 'gnb-people';
  }

  /**
   * Aggregate people from gnb-resolutions:
   * - by name prefix
   * - optional PersonType
   */
  public async aggregateBy(
    namePrefix: string,
    type?: PersonType
  ): Promise<any> {
    const query = JSON.parse(JSON.stringify(aggsPeopleWithName));

    if (type) {
      query.people.aggs.filter_people.filter.bool.must.push(new FilterPersonType(type));
    }

    namePrefix.split(' ').forEach(np => {
      query.people.aggs.filter_people.filter.bool.must.push(new FilterPersonName(np));
    });

    const response = await this.esClient
      .search(new AggsRequest(query))
      .catch(e => handleEsError(e, ERR_ES_AGGREGATE_PEOPLE));
    return response.aggregations.people.filter_people.sum_people_id.buckets;
  }

  /**
   * Get multiple people from gnb-people
   */
  public async getMulti(
    ids: number[]
  ): Promise<Person[]> {
    if (ids.length === 0) {
      return [];
    }
    const params = {index: this.index, body: {ids}};
    let response: MGetResponse<Person> = await this.esClient
      .mget<Person>(params)
      .catch(e => handleEsError(e, ERR_ES_GET_MULTI_PEOPLE));

    if (response.docs) {
      return response.docs.map((d: any) => d._source) as Person[];
    } else {
      return [];
    }

  }

}
