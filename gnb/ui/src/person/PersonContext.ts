import {createContext, useContext} from 'react';
import {Person} from "../elastic/model/Person";
import {PersonType} from "../elastic/model/PersonType";

export type PersonStateType = {
  person: Person;
  type: PersonType;
}

export type PersonContextType = {
  personState: PersonStateType;
  setPersonState: (s: PersonStateType) => void
}

/**
 * TODO: Make configurable
 */
export const defaultPersonContext = {
  personState: {
    person: {
      id: 360496,
      familyName: "Rode",
      firstNames: "Anthonis",
      interpositions: "de",
      quality: "schepen en vroedschap van Utrecht",
      functions: [
        {
          "id": 86401,
          "name": "gedeputeerde ter Staten-Generaal",
          "start": "1626-01-01",
          "end": "1630-01-01"
        }
      ]
    } as Person,
    type: PersonType.ATTENDANT
  },
  setPersonState: dummy
} as PersonContextType;

export const PersonContext = createContext<PersonContextType>(defaultPersonContext);

export const usePersonContext = () => useContext(PersonContext);

function dummy() {
  console.warn('no context provider');
}
