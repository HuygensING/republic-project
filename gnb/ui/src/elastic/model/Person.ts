import {PersonFunction} from "./PersonFunction";

export type Person = {
  id: number;
  searchName: string;
  firstNames: string;
  interpositions: string;
  familyName: string;
  nameType?: string;
  functions: PersonFunction[];
  mentionedCount: number;
  attendantCount: number;
}
