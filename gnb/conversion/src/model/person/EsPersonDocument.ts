import EsDocument from "../EsDocument";
import {PersonFunction} from "./PersonFunction";
import {Metadata} from "./Metadata";

export default class EsPersonDocument extends EsDocument {

  public searchName: string;
  public firstNames: string;
  public familyName: string;
  public prepositions: string;
  public interpositions: string;
  public postpositions: string;
  public nameType: string;
  public quality: string;
  public functions: PersonFunction[];
  public metadata: Metadata;
  public category: string;
  public attendantCount: number;
  public mentionedCount: number;

  constructor(
    id: string,
    metadata: Metadata
  ) {
    super(id);
    this.metadata = metadata;
  }
}
