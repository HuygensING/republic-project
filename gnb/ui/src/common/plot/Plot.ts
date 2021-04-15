import {renderHeatmap} from "./Heatmap";
import {MutableRefObject} from "react";
import {renderHistogram} from "./Histogram";
import {PlotConfig} from "./PlotConfig";
import {resetCanvas} from "./D3Canvas";
import {DataEntry} from "./DataEntry";

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
  resetCanvas(canvasRef, type);
  return functionRef(canvasRef, data, config, handleBarClick);
}
