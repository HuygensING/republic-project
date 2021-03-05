import {Client} from "elasticsearch";
import ResolutionRequest from "./query/aggs/ResolutionRequest";
import FilterRange from "./query/filter/FilterRange";
import AggsResolutionHistogram from "./query/aggs/AggsResolutionHistogram";
import {PersonType} from "./model/PersonType";
import FilterFullText from "./query/filter/FilterFullText";
import FilterPerson from "./query/filter/FilterPerson";
import Resolution from "./model/Resolution";

import {
  ERR_ES_AGGREGATE_RESOLUTIONS,
  ERR_ES_AGGREGATE_RESOLUTIONS_BY_PERSON,
  ERR_ES_GET_MULTI_RESOLUTIONS
} from "../content/Placeholder";
import {handleEsError} from "./EsErrorHandler";
import AggWithIdFilter from "./query/aggs/AggWithIdFilter";
import AggWithFilters from "./query/aggs/AggWithFilters";
import Request from "./query/Request";
import {QueryWithIdsAndHighlights} from "./query/QueryWithIdsAndHighlights";
import Place from "../view/model/Place";
import {Term} from "../view/model/Term";
import FilterAnnotation from "./query/filter/FilterAnnotation";
import {PersonFunction} from "./model/PersonFunction";
import FilterPeople from "./query/filter/FilterPeople";

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
    fullText: string,
    places: Place[],
    functions: PersonFunction[]
  ): Promise<any> {
    const query = new AggWithFilters();

    query.addFilter(new FilterRange(begin, end));

    if (fullText) {
      query.addFilter(new FilterFullText(fullText));
    }

    for (const a of attendants) {
      query.addFilter(new FilterPerson(a, PersonType.ATTENDANT));
    }

    for (const m of mentioned) {
      query.addFilter(new FilterPerson(m, PersonType.MENTIONED));
    }

    for (const p of places) {
      query.addFilter(new FilterAnnotation('plaats', p.val));
    }

    for (const f of functions) {
      query.addFilter(new FilterPeople(f.people));
    }

    const hist = new AggsResolutionHistogram(begin, end, 1);
    query.addAgg(hist);

    const response = await this.esClient
      .search(new ResolutionRequest(query))
      .catch(e => handleEsError(e, ERR_ES_AGGREGATE_RESOLUTIONS));

    return response.aggregations
      .filtered_aggs
      .resolution_histogram
      .buckets;
  }

  /**
   * Get multiple resolutions from gnb-resolutions
   * @param ids resolution IDs
   * @param highlight using simple query format
   */
  public async getMulti(
    ids: string[],
    highlight: string
  ): Promise<Resolution[]> {
    if (ids.length === 0) {
      return [];
    }
    const request = new Request(this.index, new QueryWithIdsAndHighlights(ids, highlight));
    const response = await this.esClient
      .search<Resolution>(request)
      .catch(e => handleEsError(e, ERR_ES_GET_MULTI_RESOLUTIONS));

    if (response.hits) {
      return response.hits.hits.map(d => {
        const result = d._source;
        if (d.highlight) {
          result.resolution.originalXml = d.highlight['resolution.originalXml'][0];
        }
        return result;
      }) as Resolution[];
    } else {
      return [];
    }
  }

  public async aggregateByPerson(
    resolutions: string[],
    id: number,
    type: PersonType,
    begin: Date,
    end: Date
  ): Promise<Resolution[]> {

    if (resolutions.length === 0) {
      return [];
    }

    const filteredQuery = new AggWithFilters();
    filteredQuery.addFilter(new FilterPerson(id, type));

    return await this.aggregateByResolutionsAndFilters(resolutions, filteredQuery, begin, end);
  }

  public async aggregateByTerm(
    resolutions: string[],
    term: Term,
    begin: Date,
    end: Date
  ): Promise<Resolution[]> {

    if (resolutions.length === 0) {
      return [];
    }

    const filteredQuery = new AggWithFilters();
    filteredQuery.addFilter(new FilterFullText(term.val));

    return await this.aggregateByResolutionsAndFilters(resolutions, filteredQuery, begin, end);
  }

  public async aggregateByPlace(
    resolutions: string[],
    place: Place,
    begin: Date,
    end: Date
  ): Promise<Resolution[]> {

    if (resolutions.length === 0) {
      return [];
    }

    const filteredQuery = new AggWithFilters();
    filteredQuery.addFilter(new FilterAnnotation('plaats', place.val));

    return await this.aggregateByResolutionsAndFilters(resolutions, filteredQuery, begin, end);
  }

  public async aggregateByFunction(
    resolutions: string[],
    personFunction: PersonFunction,
    begin: Date,
    end: Date
  ): Promise<Resolution[]> {

    if (resolutions.length === 0) {
      return [];
    }

    const filteredQuery = new AggWithFilters();
    filteredQuery.addFilter(new FilterPeople(personFunction.people));
    return await this.aggregateByResolutionsAndFilters(resolutions, filteredQuery, begin, end);
  }

  private async aggregateByResolutionsAndFilters(
    resolutions: string[],
    filteredQuery: AggWithFilters,
    begin: Date,
    end: Date
  ) {
    const sortedResolutions = resolutions.sort();
    filteredQuery.addAgg(new AggsResolutionHistogram(begin, end, 1));

    const aggWithIdFilter = new AggWithIdFilter(sortedResolutions);
    aggWithIdFilter.addAgg(filteredQuery);

    const aggsQuery = new ResolutionRequest(aggWithIdFilter);

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
