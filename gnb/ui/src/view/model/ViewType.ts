import {PersonType} from "../../elastic/model/PersonType";
import {ERR_NOT_A_PERSON, ERR_NOT_A_VIEW_TYPE_VALUE} from "../../Placeholder";
import {Term} from "./Term";
import {Person} from "../../elastic/model/Person";
import Location from "./Location";

export enum ViewType {
  ATTENDANT = 'attendant',
  MENTIONED = 'mentioned',
  TERM = 'term',
  LOCATION = 'location'
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

export function toString(entity: Person | Term | Location) {
  if((entity as Person).id !== undefined) {
    return (entity as Person).id;
  }
  if((entity as Term).val !== undefined) {
    return (entity as Term).val;
  }
  if((entity as Location).val !== undefined) {
    return (entity as Location).val;
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
