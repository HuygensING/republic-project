import {renderHeatmap} from "./Heatmap";
import {MutableRefObject} from "react";
import {HistogramBar, renderHistogram} from "./Histogram";
import {PlotConfig} from "./PlotConfig";

export enum PlotType {
  HISTOGRAM = 'histogram',
  HEATMAP = 'heatmap'
}

const functions = [
  {type: PlotType.HISTOGRAM, functionRef: renderHistogram},
  {type: PlotType.HEATMAP, functionRef: renderHeatmap}
];

export default function renderPlot(
  type: PlotType,
  canvasRef: MutableRefObject<any>,
  bars: HistogramBar[],
  config: PlotConfig,
  handleBarClick: (r: string[]) => void,
) {
  if(!canvasRef || !bars.length) {
    return;
  }
  let functionRef = functions.find(f => f.type === type)?.functionRef;
  if (!functionRef) {
    functionRef = renderHistogram;
  }
  return functionRef(canvasRef, bars, config, handleBarClick);

}
