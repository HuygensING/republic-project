import {createContext, useContext} from 'react';
import {BaseStateType, defaultBaseContext, dummy, reducer} from "../../BaseStateType";
import {PlotType} from "./Plot";

export type PlotStateType = BaseStateType & {
  type: PlotType;
}

export type PlotContextType = {
  plotState: PlotStateType;
  setPlotState: (a: PlotStateType) => void
}

export const defaultPlotContext = {
  plotState: {
    ...defaultBaseContext,
    type: PlotType.HEATMAP
  },
  setPlotState: dummy
} as PlotContextType;

export const PlotContext = createContext<PlotContextType>(defaultPlotContext);

export const usePlotContext = () => useContext(PlotContext);

export const plotReducer : (<T extends PlotStateType>(s: T, a: T) => T) = reducer;
