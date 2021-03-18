import BaseSearchParams from "./BaseSearchParams";
import {Query} from "../query/query/Query";

export default class PeopleSearchParams extends BaseSearchParams {
  constructor(query: Query) {
    super("gnb-people", query);
  }
}
