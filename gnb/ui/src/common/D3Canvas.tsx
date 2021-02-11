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
    <svg
      className="d3-canvas"
      ref={ref}
    >
      <g className="plot-area"/>
      <g className="x-axis"/>
      <g className="y-axis"/>
    </svg>
  );
}, areEqual);
