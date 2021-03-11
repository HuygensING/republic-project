import Request from "../Request";

export default class PeopleRequest extends Request {
  constructor(aggs: any) {
    super("gnb-people", aggs);
  }
}
