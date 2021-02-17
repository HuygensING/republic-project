import {createContext, useContext} from 'react';
import {Person} from "../elastic/model/Person";
import {BaseStateType, defaultBaseContext, dummy, reducer} from "../BaseStateType";
import {ViewType} from "./model/ViewType";
import {Term} from "./model/Term";
import Location from "./model/Location";

export type ViewStateType = BaseStateType & {
  views: {
    type: ViewType,
    entity: Person | Term | Location
  }[];
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
