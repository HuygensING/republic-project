import {renderHeatmap} from "../common/Heatmap";
import {MutableRefObject} from "react";
import {HistogramBar, renderHistogram} from "../common/Histogram";
import {HistogramConfig} from "../common/PlotConfig";

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
  config: HistogramConfig,
  handleBarClick: (r: string[]) => void,
) {
  if(!canvasRef) {
    return;
  }
  let functionRef = functions.find(f => f.type === type)?.functionRef;
  if (!functionRef) {
    functionRef = renderHistogram;
  }
  return functionRef(canvasRef, bars, config, handleBarClick);

}
