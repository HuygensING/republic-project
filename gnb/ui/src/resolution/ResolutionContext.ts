import {createContext, useContext} from 'react';
import {HistogramBar} from "../common/Histogram";
import {BaseStateType, defaultBaseContext, dummy} from "../BaseStateType";

export type ResolutionStateType = BaseStateType & {
  resolutions: HistogramBar[];
}

export type ResolutionContextType = {
  resolutionState: ResolutionStateType;
  setResolutionState: (a: ResolutionStateType) => void
}

export const defaultResolutionContext = {
  resolutionState: {
    ...defaultBaseContext,
    resolutions: []
  },
  setResolutionState: dummy
} as ResolutionContextType;

export const ResolutionContext = createContext<ResolutionContextType>(defaultResolutionContext);

export const useResolutionContext = () => useContext(ResolutionContext);
