import {Client, MGetResponse} from "elasticsearch";
import queryWithSort from './query/query/query-with-sort.json';
import {Person} from "./model/Person";
import {PersonType} from "./model/PersonType";
import {ERR_ES_AGGREGATE_PEOPLE, ERR_ES_GET_MULTI_PEOPLE} from "../content/Placeholder";
import {handleEsError} from "./EsErrorHandler";
import clone from "../util/clone";
import PeopleRequest from "./query/aggs/PeopleRequest";
import FilterSearchName from "./query/filter/FilterSearchName";

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
    const query = clone<any>(queryWithSort);

    if (type == PersonType.ATTENDANT) {
      query.query.bool.must.push({"range": {"attendantCount" : { "gte": 0 }}});
      query.sort.push({ "attendantCount" : {"order" : "desc"}});
    } else if (type == PersonType.MENTIONED) {
      query.query.bool.must.push({"range": {"mentionedCount": {"gte": 0}}});
      query.sort.push({ "mentionedCount" : {"order" : "desc"}});
    }

    namePrefix.split(' ').forEach(np => {
      query.query.bool.must.push(new FilterSearchName(np));
    });

    const response = await this.esClient
      .search(new PeopleRequest(query))
      .catch(e => handleEsError(e, ERR_ES_AGGREGATE_PEOPLE));
    return response.hits.hits;
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
