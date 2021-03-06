import React, {MutableRefObject} from "react";
import * as d3 from "d3";
import {PlotType} from "./Plot";

type D3CanvasProps = {
  svgRef: MutableRefObject<any>
};

function areEqual(): boolean {
  return true;
}

export function resetCanvas(ref: React.MutableRefObject<any>, type: PlotType) {
  const canvas = d3
    .select(ref.current)
    .select('.d3-canvas');

  if(canvas.attr('data-type') === type) {
    return;
  }

  canvas
    .selectAll('*')
    .remove();
  canvas.html(
    '<g class="plot-area"/>' +
    '<g class="x-axis"/>' +
    '<g class="y-axis"/>'
  );
  canvas.attr('data-type', type)
}

export const D3Canvas = React.memo<D3CanvasProps>((props) => {

  const ref = props.svgRef;
  return (
    <div
      className="d3-canvas-wrapper"
      ref={ref}
    >
      <svg className="d3-canvas"/>
      <div className="d3-tooltip"/>
    </div>
  );

  }, areEqual);

export function getTooltip(canvasRef: any) {
  return d3
    .select(canvasRef.current)
    .select('.d3-tooltip');
}

export function showTooltip(
  canvasRef: any,
  label: string,
  color: string,
  x: number,
  y: number
) {

  const tooltip = getTooltip(canvasRef);
  const tooltipSize = (tooltip.node() as any).getBoundingClientRect();
  const left = Math.round(x - (tooltipSize.width / 2));

  tooltip.transition()
    .duration(200)
    .style('visibility', 'visible');

  let labelEl = `<span class="tooltip-label" style="background: ${color}">${label}</span>`;

  tooltip.html(labelEl)
    .style('left', left + 'px')
    .style('top', Math.round(y - 1.25 * tooltipSize.height) + 'px');
}

