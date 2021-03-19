import {PersonAnn} from "./PersonAnn";
import {Ann} from "./Ann";

export default interface Resolution {
  id: string;
  metadata: {
    meeting: { date: string },
    resolution: number
  };
  source: string;
  indexedOn: string;
  people: PersonAnn[];
  resolution: {
    postprandum: boolean;
    plainText: string;
    originalXml: string;
  }
  annotations: Ann[]

}

