import {PersonType} from "../elastic/model/PersonType";
import {ATTENDANT, MENTIONED, SEARCH_TERM} from "../Placeholder";

export type ViewType = {
  name: string,
  personType?: PersonType,
  placeholder: string
};

export const ViewTypes = {
  ATTENDANT: {
    name: PersonType.ATTENDANT,
    personType: PersonType.ATTENDANT,
    placeholder: ATTENDANT
  },
  MENTIONED: {
    name: PersonType.MENTIONED,
    personType: PersonType.MENTIONED,
    placeholder: MENTIONED
  },
  TERM: {
    name: 'term',
    placeholder: SEARCH_TERM
  }
};
