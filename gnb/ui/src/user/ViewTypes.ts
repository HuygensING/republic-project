import {PersonType} from "../elastic/model/PersonType";
import {ATTENDANT, MENTIONED, SEARCH_TERM} from "../Placeholder";

export type ViewType = {
  type: string,
  personType?: PersonType,
  placeholder: string
};

export const ViewTypes: ViewType[] = [
  {
    type: 'attendant',
    personType: PersonType.ATTENDANT,
    placeholder: ATTENDANT
  },
  {
    type: 'mentioned',
    personType: PersonType.MENTIONED,
    placeholder: MENTIONED
  },
  {
    type: 'term',
    placeholder: SEARCH_TERM
  }
];
