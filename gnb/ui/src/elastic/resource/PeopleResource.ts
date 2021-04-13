import {Client, MGetResponse} from "elasticsearch";
import {Person} from "../model/Person";
import {PersonType} from "../model/PersonType";
import {ERR_ES_AGGREGATE_PEOPLE, ERR_ES_GET_MULTI_PEOPLE} from "../../content/Placeholder";
import {handleEsError} from "../EsErrorHandler";
import FilterSearchName from "../query/filter/people/FilterSearchName";
import {BodyWithSort} from "../query/body/BodyWithSort";
import FilterIsAttendant from "../query/filter/people/FilterIsAttendant";
import FilterIsMentioned from "../query/filter/people/FilterIsMentioned";
import SortAttendantCount from "../query/sort/SortAttendantCount";
import SortMentionedCount from "../query/sort/SortMentionedCount";
import PeopleSearchParams from "../query/search-params/PeopleSearchParams";

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
    const query = new BodyWithSort();

    if (type === PersonType.ATTENDANT) {
      query.addFilter(new FilterIsAttendant());
      query.addSort(new SortAttendantCount("desc"));
    } else if (type === PersonType.MENTIONED) {
      query.addFilter(new FilterIsMentioned());
      query.addSort(new SortMentionedCount("desc"));
    }

    namePrefix.split(' ').forEach(np => {
      query.addFilter(new FilterSearchName(np));
    });

    const params = new PeopleSearchParams(query);
    const response = await this.esClient
      .search(params)
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
