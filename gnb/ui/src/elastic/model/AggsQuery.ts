import EsQuery from "./EsQuery";
import {AggsBody} from "./AggsBody";

export default class AggsQuery extends EsQuery {
  constructor(aggs: any) {
    super("gnb-resolutions", new AggsBody(aggs));
  }
}
