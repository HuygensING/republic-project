import SearchParams from "../SearchParams";
import {Body} from "../body/Body";

export default class PeopleSearchParams extends SearchParams {
  constructor(query: Body) {
    super("gnb-people", query);
  }
}
