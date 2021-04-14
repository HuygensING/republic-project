import React, {MutableRefObject} from "react";

type D3CanvasProps = {
  svgRef: MutableRefObject<any>
};

function areEqual(): boolean {
  return true;
}

export const D3Canvas = React.memo<D3CanvasProps>((props) => {

  const ref = props.svgRef;

  return (
    <div
      className="d3-canvas-wrapper"
      ref={ref}
    >
      <svg
        className="d3-canvas"
      >
        <g className="plot-area"/>
        <g className="x-axis"/>
        <g className="y-axis"/>
      </svg>
      <div className="d3-tooltip"/>
    </div>
  );
}, areEqual);
