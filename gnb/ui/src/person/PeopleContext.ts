import {createContext, useContext} from 'react';
import {Person} from "../elastic/model/Person";
import {PersonType} from "../elastic/model/PersonType";
import {BaseStateType, defaultBaseContext, dummy, reducer} from "../BaseStateType";

export type PersonWithType = {
  person: Person;
  type: PersonType
};
export type PeopleStateType = BaseStateType & {
  people: PersonWithType[];
}

export type PeopleContextType = {
  peopleState: PeopleStateType;
  setPeopleState: (s: PeopleStateType) => void
}

/**
 * TODO: Make configurable
 */
export const defaultPeopleContext = {
  peopleState: {
    ...defaultBaseContext,
    people: [{
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
    }, {
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
    }]
  },
  setPeopleState: dummy
} as PeopleContextType;

export const PeopleContext = createContext<PeopleContextType>(defaultPeopleContext);

export const usePeopleContext = () => useContext(PeopleContext);

export const peopleReducer : (<T extends PeopleStateType>(s: T, a: T) => T) = reducer;
