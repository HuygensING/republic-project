import {Metadata} from "./resolution/Metadata";
import {Resolution} from "./resolution/Resolution";
import {Annotation} from "./resolution/Annotation";
import {Person} from "./resolution/Person";

export default class EsDocument {
  public id: string;

  constructor(
    id: string,
  ) {
    this.id = id;
  }
}
