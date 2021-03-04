import Request from "../Request";
import {AggsQuery} from "./AggsQuery";

export default class ResolutionRequest extends Request {
  constructor(aggs: any) {
    super("gnb-resolutions", new AggsQuery(aggs));
  }
}
