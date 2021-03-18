import SearchParams from "../SearchParams";
import AggsBody from "../body/AggsBody";

export default class ResolutionAggsSearchParams extends SearchParams {
  constructor(aggs: any) {
    super("gnb-resolutions", new AggsBody(aggs));
  }
}
