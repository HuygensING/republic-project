import {renderHeatmap} from "./Heatmap";
import {MutableRefObject} from "react";
import {DataEntry, renderHistogram} from "./Histogram";
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
  data: DataEntry[],
  config: PlotConfig,
  handleBarClick: (r: string[]) => void,
) {
  if(!canvasRef || !data.length) {
    return;
  }
  let functionRef = functions.find(f => f.type === type)?.functionRef;
  if (!functionRef) {
    functionRef = renderHistogram;
  }
  return functionRef(canvasRef, data, config, handleBarClick);

}
