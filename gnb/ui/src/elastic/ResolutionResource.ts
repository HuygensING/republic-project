import {Client} from "elasticsearch";
import AggsQuery from "./model/AggsQuery";
import aggsWithFilters from './model/aggs-with-filters.json';
import AggsFilterRange from "./model/AggsFilterRange";
import AggsResolutionHistogram from "./model/AggsResolutionHistogram";
import {PersonType} from "./model/PersonType";
import AggsFilterFullText from "./model/AggsFilterFullText";
import AggsFilterPeople from "./model/AggsFilterPeople";
import Resolution from "./model/Resolution";

import {ERR_ES_AGGREGATE_RESOLUTIONS, ERR_ES_GET_MULTI_RESOLUTIONS} from "../Placeholder";
import {handleEsError} from "./EsErrorHandler";

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

    aggs.aggs = new AggsResolutionHistogram(begin, end, 1);

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

}
