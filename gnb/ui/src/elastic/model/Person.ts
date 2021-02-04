import {PersonType} from "./PersonType";

export interface Person {
  id: number;
  firstNames: string;
  interpositions: string;
  familyName: string;
  nameType: string;
  functions: any[];
}

export type PersonAnn = {
  id: number;
  type: PersonType;
  province?: string;
  name: string;
}

export function toName(person: Person) {
  let result = '';
  if (person.firstNames) {
    result += person.firstNames + ' ';
  }
  if (person.interpositions) {
    result += person.interpositions + ' '
  }
  if (person.familyName) {
    result += person.familyName + ' '
  }
  if (person.nameType) {
    result += person.nameType + ' '
  }
  return result.trim();
}
