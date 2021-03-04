import {createContext, useContext} from 'react';
import {BaseStateType, defaultBaseContext, dummy, reducer} from "../BaseStateType";
import {ViewType} from "./model/ViewType";
import {ViewEntityType} from "./model/ViewEntityType";

export type ViewStateType = BaseStateType & {
  views: {
    type: ViewType,
    entity: ViewEntityType
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
