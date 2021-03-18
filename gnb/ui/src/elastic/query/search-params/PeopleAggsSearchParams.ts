import SearchParams from "../SearchParams";
import {AggsQuery} from "../query/AggsQuery";

export default class PeopleAggsSearchParams extends SearchParams {
  constructor(aggs: any) {
    super("gnb-people", new AggsQuery(aggs));
  }
}
