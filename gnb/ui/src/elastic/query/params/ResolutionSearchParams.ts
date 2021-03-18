import SearchParams from "../SearchParams";
import {AggsQuery} from "../query/AggsQuery";

export default class ResolutionSearchParams extends SearchParams {
  constructor(aggs: any) {
    super("gnb-resolutions", new AggsQuery(aggs));
  }
}
