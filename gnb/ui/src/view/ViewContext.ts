import {createContext, useContext} from 'react';
import {Person} from "../elastic/model/Person";
import {BaseStateType, defaultBaseContext, dummy, reducer} from "../BaseStateType";
import {ViewType} from "./ViewTypes";
import {Term} from "./Term";

export type ViewStateType = BaseStateType & {
  views: {
    type: ViewType,
    entity: Person | Term
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
