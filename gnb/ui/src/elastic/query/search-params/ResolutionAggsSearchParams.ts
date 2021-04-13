import SearchParams from "../SearchParams";
import BodyWithAggs from "../body/BodyWithAggs";

export default class ResolutionAggsSearchParams extends SearchParams {
  constructor(aggs: any) {
    super("gnb-resolutions", new BodyWithAggs(aggs));
  }
}
