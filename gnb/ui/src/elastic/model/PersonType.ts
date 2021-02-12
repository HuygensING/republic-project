import {ATTENDANT, ERR_VIEW_TYPE_NOT_FOUND, MENTIONED} from "../../Placeholder";

export enum PersonType {
  ATTENDANT = 'attendant',
  MENTIONED = 'mentioned'
}

export function toPlaceholder(type: PersonType) {
  switch (type) {
    case PersonType.ATTENDANT:
      return ATTENDANT;
    case PersonType.MENTIONED:
      return MENTIONED;
    default:
      throw Error(`${ERR_VIEW_TYPE_NOT_FOUND}: ${type} `);
  }

}
