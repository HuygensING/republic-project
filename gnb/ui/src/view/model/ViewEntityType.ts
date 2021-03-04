import {Person} from "../../elastic/model/Person";
import {Term} from "./Term";
import Place from "./Place";
import {PersonFunction} from "../../elastic/model/PersonFunction";

export type ViewEntityType = Person | Term | Place | PersonFunction;


export function toString(entity: ViewEntityType) {
  if((entity as Person).id !== undefined) {
    return (entity as Person).id;
  }
  if((entity as Term).val !== undefined) {
    return (entity as Term).val;
  }
  if((entity as Place).val !== undefined) {
    return (entity as Place).val;
  }
}
