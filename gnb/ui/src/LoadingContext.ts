import {createContext, useContext} from 'react';
import {BaseStateType, defaultBaseContext, dummy} from "./BaseStateType";
import clone from "./util/clone";
import * as _ from "lodash";

export type LoadingStateType = BaseStateType & {
  loading?: boolean,
  loadingEvents: string[];
}
export type LoadingEvent = {event: string, loading: boolean};
export type LoadingContextType = {
  loadingState: LoadingStateType;
  setLoadingState: (s: LoadingEvent) => void
}

export const defaultLoadingContext = {
  loadingState: {
    ...defaultBaseContext,
    loading: false,
    loadingEvents: []
  },
  setLoadingState: dummy
} as LoadingContextType;

export const LoadingContext = createContext<LoadingContextType>(defaultLoadingContext);

export const useLoadingContext = () => useContext(LoadingContext);
export const useLoading = () => useContext(LoadingContext).loadingState.loading;

/**
 * Set event when loading, remove event when not loading
 * Set overal loading status to true, when a single loading event exists
 */
export function loadingReducer(state: LoadingStateType, action: LoadingEvent) {
  const result = clone<LoadingStateType>(state);
  if(action.loading) {
    result.loadingEvents.push(action.event);
  } else {
    _.remove(result.loadingEvents, (n) => n === action.event);
  }
  result.loading = result.loadingEvents.length > 0;
  return result;
}

