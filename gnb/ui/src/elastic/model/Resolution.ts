import {Person} from "./Person";

export default interface Resolution {
  id: string;
  metadata: {
    meeting: { date: string }
  };
  source: string;
  indexedOn: string;
  people: Person[];
  resolution: {
    postprandum: boolean;
    plainText: string;
    originalXml: string;
  }
  annotations: [
    {
      id: number;
      name: string;
      value: string;
    }
  ]

}


