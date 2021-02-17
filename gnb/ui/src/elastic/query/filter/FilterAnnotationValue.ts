import {Filter} from "./Filter";

export default class FilterAnnotationValue implements Filter {
  public prefix: any;

  constructor(prefix: string) {
    this.prefix = { "annotations.value": { "value": prefix }};
  }
}
