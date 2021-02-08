import React, {MutableRefObject} from "react";

type D3CanvasProps = {
  svgRef: MutableRefObject<any>
};

function areEqual(): boolean {
  return true;
}

export const D3Canvas = React.memo<D3CanvasProps>((props) => {
  console.log('create canvas');
  const ref = props.svgRef;

  return (
    <svg
      ref={ref}
      style={{
        height: "15em",
        width: "100%",
        marginRight: "0px",
        marginLeft: "0px",
      }}
    >
      <g className="plot-area"/>
      <g className="x-axis"/>
      <g className="y-axis"/>
    </svg>
  );
}, areEqual);
