import BaseSearchParams from "./BaseSearchParams";
import {AggsQuery} from "../query/query/AggsQuery";

export default class PeopleAggsSearchParams extends BaseSearchParams {
  constructor(aggs: any) {
    super("gnb-people", new AggsQuery(aggs));
  }
}
