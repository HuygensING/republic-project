import {PersonType} from "../../elastic/model/PersonType";
import {ERR_NOT_A_PERSON, ERR_NOT_A_VIEW_TYPE_VALUE} from "../../content/Placeholder";

export enum ViewType {
  ATTENDANT = 'attendant',
  MENTIONED = 'mentioned',
  TERM = 'term',
  PLACE = 'place',
  FUNCTION = 'function'
}

export function isPerson(type: ViewType) : boolean {
  return [ViewType.ATTENDANT, ViewType.MENTIONED].includes(type);
}

export function toPerson(type: ViewType) : PersonType {
  if(ViewType.MENTIONED === type) {
    return PersonType.MENTIONED;
  }
  if(ViewType.ATTENDANT === type) {
    return PersonType.ATTENDANT;
  }
  throw Error(`${ERR_NOT_A_PERSON}: ${type}`);
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
