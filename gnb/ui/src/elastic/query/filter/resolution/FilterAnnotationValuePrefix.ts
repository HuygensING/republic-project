import {Filter} from "../Filter";

export default class FilterAnnotationValuePrefix implements Filter {
  public prefix: any;

  constructor(prefix: string) {
    this.prefix = { "annotations.value": { "value": prefix }};
  }
}
