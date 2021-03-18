import SearchParams from "../SearchParams";
import {AggsQuery} from "../query/AggsQuery";

export default class ResolutionAggsSearchParams extends SearchParams {
  constructor(aggs: any) {
    super("gnb-resolutions", new AggsQuery(aggs));
  }
}
