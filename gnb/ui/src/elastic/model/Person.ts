import {Agg} from "../query/aggs/Agg";

export type Person = {
  id: number;
  firstNames: string;
  interpositions: string;
  familyName: string;
  nameType?: string;
  functions: any[];
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

