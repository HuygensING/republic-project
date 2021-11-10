import {Person} from "../model/resolution/Person";
import EsPersonDocument from "../model/person/EsPersonDocument";

export function toName(person: EsPersonDocument) {
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

