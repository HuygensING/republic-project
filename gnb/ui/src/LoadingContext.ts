import {createContext, useContext} from 'react';
import {BaseStateType, defaultBaseContext, dummy} from "./BaseStateType";
import clone from "./util/clone";

export type LoadingStateType = BaseStateType & {
  loading?: boolean,
  loadingEvents: Map<string, boolean>
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
    loadingEvents: new Map<string, boolean>()
  },
  setLoadingState: dummy
} as LoadingContextType;

export const LoadingContext = createContext<LoadingContextType>(defaultLoadingContext);

export const useLoadingContext = () => useContext(LoadingContext);
export const useLoading = () => useContext(LoadingContext).loadingState.loading;

export function loadingReducer(state: LoadingStateType, action: LoadingEvent) {
  const result = clone<LoadingStateType>(state);
  result.loadingEvents.set(action.event, action.loading);
  const foundLoading = Array.from(result.loadingEvents.entries()).find(([, v]) => v);
  result.loading = !!foundLoading;
  return result;
}
