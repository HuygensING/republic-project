import {createContext, useContext} from 'react';
import {BaseStateType, defaultBaseContext, dummy, reducer} from "./BaseStateType";

export type LoadingStateType = BaseStateType & {
  loading?: boolean,
  resolutionsLoading?: boolean
}

export type LoadingContextType = {
  loadingState: LoadingStateType;
  setLoadingState: (s: LoadingStateType) => void
}

export const defaultLoadingContext = {
  loadingState: {
    ...defaultBaseContext,
    loading: false,
    resolutionsLoading: false
  },
  setLoadingState: dummy
} as LoadingContextType;

export const LoadingContext = createContext<LoadingContextType>(defaultLoadingContext);

export const useLoadingContext = () => useContext(LoadingContext);
export const useLoading = () => useContext(LoadingContext).loadingState.loading;

// export const loadingReducer : (<T extends LoadingStateType>(s: T, a: T) => T) = reducer;

export function loadingReducer(state: any, action: any) {
  console.log('loading?', state, action);
  let loading = true;
  for(const f of Object.keys(defaultLoadingContext.loadingState)) {
    if(action[f] === undefined) {
      action[f] = state[f];
    }
    if(f !== "loading" && action[f] === false) {
      loading = false;
    }
  }
  console.log('loading: ', loading);
  action.loading = loading;
  const result = reducer(state, action);
  console.log('result', result);
  return result;
}
