import Request from "../Request";
import {AggsQuery} from "./AggsQuery";

export default class AggsRequest extends Request {
  constructor(aggs: any) {
    super("gnb-resolutions", new AggsQuery(aggs));
  }
}
