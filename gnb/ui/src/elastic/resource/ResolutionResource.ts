import {Client} from "elasticsearch";
import FilterRange from "../query/filter/resolution/FilterRange";
import AggResolutionHistogram from "../query/aggs/resolution/AggResolutionHistogram";
import {PersonType} from "../model/PersonType";
import FilterFullText from "../query/filter/resolution/FilterFullText";
import FilterPerson from "../query/filter/resolution/FilterPerson";
import Resolution from "../model/Resolution";

import {
  ERR_ES_AGGREGATE_RESOLUTIONS,
  ERR_ES_AGGREGATE_RESOLUTIONS_BY_PERSON,
  ERR_ES_GET_MULTI_RESOLUTIONS
} from "../../content/Placeholder";
import {handleEsError} from "../EsErrorHandler";
import AggWithIdFilter from "../query/aggs/AggWithIdFilter";
import AggWithFilters from "../query/aggs/AggWithFilters";
import SearchParams from "../query/SearchParams";
import {BodyWithIdsAndHighlights} from "../query/body/resolution/BodyWithIdsAndHighlights";
import Place from "../../view/model/Place";
import {Term} from "../../view/model/Term";
import FilterAnnotation from "../query/filter/resolution/FilterAnnotation";
import {PersonFunction} from "../model/PersonFunction";
import FilterPeople from "../query/filter/resolution/FilterPeople";
import {PersonFunctionCategory} from "../model/PersonFunctionCategory";
import ResolutionAggsSearchParams from "../query/search-params/ResolutionAggsSearchParams";
import {BodyWithIds} from "../query/body/resolution/BodyWithIds";

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
    functions: PersonFunction[],
    functionCategories: PersonFunctionCategory[]
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
      query.addFilter(new FilterPeople(f.people, PersonType.MENTIONED));
    }

    for (const f of functionCategories) {
      query.addFilter(new FilterPeople(f.people, PersonType.MENTIONED));
    }

    const hist = new AggResolutionHistogram(begin, end, 1);
    query.addAgg(hist);

    const params = new ResolutionAggsSearchParams(query);
    const response = await this.esClient
      .search(params)
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
    highlight?: string
  ): Promise<Resolution[]> {
    if (ids.length === 0) {
      return [];
    }
    const request = highlight
      ? new SearchParams(this.index, new BodyWithIdsAndHighlights(ids, highlight))
      : new SearchParams(this.index, new BodyWithIds(ids));

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
    filteredQuery.addFilter(new FilterPeople(personFunction.people, PersonType.MENTIONED));
    return await this.aggregateByResolutionsAndFilters(resolutions, filteredQuery, begin, end);
  }

  public async aggregateByFunctionCategory(
    resolutions: string[],
    personFunctionCategory: PersonFunctionCategory,
    begin: Date,
    end: Date
  ): Promise<Resolution[]> {

    if (resolutions.length === 0) {
      return [];
    }

    const filteredQuery = new AggWithFilters();
    filteredQuery.addFilter(new FilterPeople(personFunctionCategory.people, PersonType.MENTIONED));
    return await this.aggregateByResolutionsAndFilters(resolutions, filteredQuery, begin, end);
  }

  private async aggregateByResolutionsAndFilters(
    resolutions: string[],
    filteredQuery: AggWithFilters,
    begin: Date,
    end: Date
  ) {
    const sortedResolutions = resolutions.sort();
    filteredQuery.addAgg(new AggResolutionHistogram(begin, end, 1));

    const aggWithIdFilter = new AggWithIdFilter(sortedResolutions);
    aggWithIdFilter.addAgg(filteredQuery);

    const params = new ResolutionAggsSearchParams(aggWithIdFilter);

    const response = await this.esClient
      .search(params)
      .catch(e => handleEsError(e, ERR_ES_AGGREGATE_RESOLUTIONS_BY_PERSON));

    return response.aggregations
      .id_filtered_aggs
      .filtered_aggs
      .resolution_histogram
      .buckets;
  }
}
