import {EsBody} from "./EsBody";

export default class EsQuery {

  public index: string;
  public body: EsBody;

  constructor(index: string, body: EsBody) {
    this.index = index;
    this.body = body;
  }
}
