import SearchParams from "../SearchParams";
import BodyWithAggs from "../body/BodyWithAggs";

export default class PeopleAggsSearchParams extends SearchParams {
  constructor(aggs: any) {
    super("gnb-people", new BodyWithAggs(aggs));
  }
}
