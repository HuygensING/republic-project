import SearchParams from "../SearchParams";
import AggsBody from "../body/AggsBody";

export default class PeopleAggsSearchParams extends SearchParams {
  constructor(aggs: any) {
    super("gnb-people", new AggsBody(aggs));
  }
}
