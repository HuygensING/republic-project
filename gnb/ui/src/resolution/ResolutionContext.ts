import {createContext, useContext} from 'react';
import {HistogramBar} from "../common/Histogram";

export type ResolutionStateType = {
  resolutions: HistogramBar[];
}

export type ResolutionContextType = {
  resolutionState: ResolutionStateType;
  setResolutionState: (s: ResolutionStateType) => void
}

export const defaultResolutionContext = {
  resolutionState: {
    resolutions: []
  },
  setResolutionState: dummy
} as ResolutionContextType;

export const ResolutionContext = createContext<ResolutionContextType>(defaultResolutionContext);

export const useResolutionContext = () => useContext(ResolutionContext);

function dummy() {
  console.warn('no context provider');
}
