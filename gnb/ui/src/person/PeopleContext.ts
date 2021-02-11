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
    people: []
  },
  setPeopleState: dummy
} as PeopleContextType;

export const PeopleContext = createContext<PeopleContextType>(defaultPeopleContext);

export const usePeopleContext = () => useContext(PeopleContext);

export const peopleReducer : (<T extends PeopleStateType>(s: T, a: T) => T) = reducer;
