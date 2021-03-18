import {Body} from "./Body";

export class BodyWithSize implements Body {
  public size: number;

  constructor() {
    this.size = 10;
  }
}
