import {Person} from "../../elastic/model/Person";
import {Term} from "./Term";
import Place from "./Place";
import {PersonFunction} from "../../elastic/model/PersonFunction";
import {ERR_UNKNOWN_VIEW_TYPE_TO_STRING} from "../../content/Placeholder";

export type ViewEntityType = Person | Term | Place | PersonFunction;


export function toStr(entity: ViewEntityType) {
  if((entity as Person).id !== undefined) {
    return (entity as Person).id;
  }
  if((entity as Term).val !== undefined) {
    return (entity as Term).val;
  }
  if((entity as Place).val !== undefined) {
    return (entity as Place).val;
  }
  if((entity as PersonFunction).name !== undefined) {
    return (entity as Place).val;
  }
  throw new Error(`${ERR_UNKNOWN_VIEW_TYPE_TO_STRING}: ${entity}`);
}
