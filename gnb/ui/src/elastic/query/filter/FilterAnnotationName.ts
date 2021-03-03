import {Filter} from "./Filter";

export default class FilterAnnotationName implements Filter {
  public match: any;

  constructor(name: string) {
    this.match = { "annotations.name": name };
  }
}
