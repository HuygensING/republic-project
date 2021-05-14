import React from "react";
import {ERR_NOT_A_PLOT_TYPE_VALUE, HEATMAP, HISTOGRAM} from "../../content/Placeholder";
import {PlotType} from "../../common/plot/Plot";
import {usePlotContext} from "../../common/plot/PlotContext";

const PlotTypes = [
  {name: PlotType.HEATMAP, placeholder: HEATMAP},
  {name: PlotType.HISTOGRAM, placeholder: HISTOGRAM},
];

export default function PlotTypeFormField() {

  const {plotState, setPlotState} = usePlotContext();

  return <>
    <div className="col-2 mr-3">
      <select
        className="form-control"
        id="select-plot-type"
        value={plotState.type}
        onChange={(e) => setPlotState({...plotState, type: fromValue(e.target.value)})}
      >
        {createOptions()}
      </select>
    </div>
  </>
}

function createOptions() {
  return Object.entries(PlotTypes).map(([name, value]) => {
    return <option
      key={name}
      value={value.name}
    >
      {value.placeholder}
    </option>
  });
}

export function fromValue(value: string) : PlotType {
  const found = Object
    .entries(PlotType)
    .find(([, t]) => t === value)
    ?.[1];
  if(!found) {
    throw Error(`${ERR_NOT_A_PLOT_TYPE_VALUE}: ${value}`);
  }
  return found;
}
