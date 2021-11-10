import {Meeting} from "./Meeting";

export class Metadata {
  public meeting: Meeting;
  public resolution: number;
  public source: string;
  public indexedOn: string;

  constructor(meeting: Meeting, source: string, indexedOn: string) {
    this.meeting = meeting;
    this.source = source;
    this.indexedOn = indexedOn;
  }
}
