import SearchParams from "../SearchParams";
import {Query} from "../query/Query";

export default class PeopleSearchParams extends SearchParams {
  constructor(query: Query) {
    super("gnb-people", query);
  }
}
