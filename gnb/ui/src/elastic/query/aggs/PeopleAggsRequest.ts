import Request from "../Request";
import {AggsQuery} from "./AggsQuery";

export default class PeopleAggsRequest extends Request {
  constructor(aggs: any) {
    super("gnb-people", new AggsQuery(aggs));
  }
}
