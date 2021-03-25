import {BodyWithSize} from "../BodyWithSize";

export class BodyWithIds extends BodyWithSize {

  private query: any;

  /**
   * Find resolutions, and highlight terms with .highlight
   *
   * @param ids resolution IDs
   * @param highlight using simple query format
   */
  constructor(ids: string[]) {
    super();
    this.size = 10000;

    this.query = {
      "ids": { "values": ids }
    };

  }

}
