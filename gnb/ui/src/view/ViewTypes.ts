import {PersonType} from "../elastic/model/PersonType";
import {ATTENDANT, ERR_NOT_A_PERSON, ERR_NOT_A_VIEW_TYPE_VALUE, MENTIONED, SEARCH_TERM} from "../Placeholder";
import {Term} from "./Term";
import {Person} from "../elastic/model/Person";

export enum ViewType {
  ATTENDANT = 'attendant',
  MENTIONED = 'mentioned',
  TERM = 'term'
}

export const ViewTypes = [
  {
    name: PersonType.ATTENDANT,
    personType: PersonType.ATTENDANT,
    placeholder: ATTENDANT
  },
  {
    name: PersonType.MENTIONED,
    personType: PersonType.MENTIONED,
    placeholder: MENTIONED
  },
  {
    name: 'term',
    placeholder: SEARCH_TERM
  }
];

export function isPerson(type: ViewType) : boolean {
  return [ViewType.ATTENDANT, ViewType.MENTIONED].includes(type);
}

export function toPerson(type: ViewType) : PersonType {
  if(!isPerson(type)) {
    throw Error(`${ERR_NOT_A_PERSON}: ${type}`);
  }
  const found = ViewTypes
    .find(t => t.personType?.valueOf() === type.valueOf())
    ?.personType;
  if(!found) {
    throw Error(`${ERR_NOT_A_PERSON}: ${type}`);
  }
  return found;
}

export function toString(entity: Person | Term) {
  if((entity as Person).id !== undefined) {
    return (entity as Person).id;
  }
  if((entity as Term).val !== undefined) {
    return (entity as Term).val;
  }
}

export function fromValue(value: string) : ViewType {
  const found = Object
    .entries(ViewType)
    .find(([, t]) => t === value)
    ?.[1];
  if(!found) {
    throw Error(`${ERR_NOT_A_VIEW_TYPE_VALUE}: ${value}`);
  }
  return found;
}
