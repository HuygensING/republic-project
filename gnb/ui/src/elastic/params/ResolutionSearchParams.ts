import BaseSearchParams from "./BaseSearchParams";
import {AggsQuery} from "../query/query/AggsQuery";

export default class ResolutionSearchParams extends BaseSearchParams {
  constructor(aggs: any) {
    super("gnb-resolutions", new AggsQuery(aggs));
  }
}
