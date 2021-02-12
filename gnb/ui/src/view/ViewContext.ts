import {createContext, useContext} from 'react';
import {Person} from "../elastic/model/Person";
import {PersonType} from "../elastic/model/PersonType";
import {BaseStateType, defaultBaseContext, dummy, reducer} from "../BaseStateType";

export type PersonWithType = {
  person: Person;
  type: PersonType
};
export type ViewStateType = BaseStateType & {
  views: PersonWithType[];
}

export type ViewContextType = {
  viewState: ViewStateType;
  setViewState: (s: ViewStateType) => void
}

export const defaultViewContext = {
  viewState: {
    ...defaultBaseContext,
    views: []
  },
  setViewState: dummy
} as ViewContextType;

export const ViewContext = createContext<ViewContextType>(defaultViewContext);

export const useViewContext = () => useContext(ViewContext);

export const viewReducer : (<T extends ViewStateType>(s: T, a: T) => T) = reducer;
