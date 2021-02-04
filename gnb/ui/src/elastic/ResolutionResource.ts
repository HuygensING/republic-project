import {Client} from "elasticsearch";
import AggsQuery from "./model/AggsQuery";
import aggsWithFilters from './model/aggs-with-filters.json';
import AggsFilterRange from "./model/AggsFilterRange";
import AggsResolutionHistogram from "./model/AggsResolutionHistogram";
import {PersonType} from "./model/PersonType";
import AggsFilterFullText from "./model/AggsFilterFullText";
import AggsFilterPeople from "./model/AggsFilterPeople";
import Resolution from "./model/Resolution";

import {
  ERR_ES_AGGREGATE_RESOLUTIONS,
  ERR_ES_AGGREGATE_RESOLUTIONS_BY_PERSON,
  ERR_ES_GET_MULTI_RESOLUTIONS
} from "../Placeholder";
import {handleEsError} from "./EsErrorHandler";
import {id2date} from "../util/id2date";
import AggWithIdFilter from "./model/AggWithIdFilter";
import AggWithFilters from "./model/AggWithFilters";

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
   * Aggregate resolutions:
   * - by attendant
   * - by mentioned
   * - between start and end date (up to and including)
   */
  public async aggregateBy(
    attendants: number[],
    mentioned: number[],
    begin: Date,
    end: Date,
    fullText: string
  ): Promise<any> {
    const query = JSON.parse(JSON.stringify(aggsWithFilters));
    const aggs = query.filtered_aggs;
    const filters: any[] = aggs.filter.bool.filter;

    filters.push(new AggsFilterRange(begin, end));

    if (fullText) {
      filters.push(new AggsFilterFullText(fullText));
    }

    for (const a of attendants) {
      filters.push(new AggsFilterPeople(a, PersonType.ATTENDANT));
    }

    for (const m of mentioned) {
      filters.push(new AggsFilterPeople(m, PersonType.MENTIONED));
    }

    const hist = new AggsResolutionHistogram(begin, end, 1);
    aggs.aggs[hist.name()] = hist.agg();

    const response = await this.esClient
      .search(new AggsQuery(query))
      .catch(e => handleEsError(e, ERR_ES_AGGREGATE_RESOLUTIONS));

    return response.aggregations
      .filtered_aggs
      .resolution_histogram
      .buckets;
  }

  /**
   * Get multiple resolutions from gnb-resolutions
   */
  public async getMulti(
    ids: string[]
  ): Promise<Resolution[]> {
    if (ids.length === 0) {
      return [];
    }
    const params = {index: this.index, body: {ids}};
      const response = await this.esClient
        .mget<Resolution>(params)
        .catch(e => handleEsError(e, ERR_ES_GET_MULTI_RESOLUTIONS));

      if (response.docs) {
        return response.docs.map(d => d._source) as Resolution[];
      } else {
        return [];
      }
  }

  /**
   * TODO: cleanup
   * @param resolutions
   * @param id
   * @param type
   */
  public async aggregateByPerson(
    resolutions: string[],
    id: number,
    type: PersonType
  ) : Promise<Resolution[]> {

    if(resolutions.length === 0) {
      return [];
    }

    const filteredQuery = new AggWithFilters();
    filteredQuery.addFilter(new AggsFilterPeople(id, type));

    const sortedResolutions = resolutions.sort();
    const begin = id2date(sortedResolutions[0]);
    const end = id2date(sortedResolutions[sortedResolutions.length - 1]);
    filteredQuery.addAgg(new AggsResolutionHistogram(begin, end, 1));

    const aggWithIdFilter = new AggWithIdFilter(sortedResolutions);
    aggWithIdFilter.addAgg(filteredQuery);

    const aggsQuery = new AggsQuery(aggWithIdFilter);

    const response = await this.esClient
      .search(aggsQuery)
      .catch(e => handleEsError(e, ERR_ES_AGGREGATE_RESOLUTIONS_BY_PERSON));

    return response.aggregations
      .id_filtered_aggs
      .filtered_aggs
      .resolution_histogram
      .buckets;

  }
}
