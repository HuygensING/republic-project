import {Metadata} from "./Metadata";
import {Resolution} from "./Resolution";
import {Annotation} from "./Annotation";
import {Person} from "./Person";
import EsDocument from "../EsDocument";

export default class EsResolutionDocument extends EsDocument {
  public metadata: Metadata;
  public people: Person[];
  public resolution: Resolution;
  public annotations: Annotation[];

  constructor(
    id: string,
    metadata: Metadata,
    people: Person[],
    resolution: Resolution,
    annotations: Annotation[]
  ) {
    super(id);
    this.metadata = metadata;
    this.people = people;
    this.resolution = resolution;
    this.annotations = annotations;
  }
}
