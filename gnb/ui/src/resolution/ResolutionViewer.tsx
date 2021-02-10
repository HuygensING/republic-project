import React, {MutableRefObject, useEffect, useRef, useState} from "react";
import ResolutionHistogram from "./ResolutionHistogram";
import {D3Canvas} from "../common/D3Canvas";
import {Texts} from "../common/Texts";
import {useResolutionContext} from "./ResolutionContext";

export default function ResolutionViewer() {

  const {resolutionState} = useResolutionContext();

  const svgRef: MutableRefObject<any> = useRef(null);
  const [hasSvg, setHasSvg] = useState(svgRef.current);

  useEffect(() => {
    setHasSvg(svgRef.current)
  }, [svgRef]);

  const [resolutions, setResolutions] = React.useState({
    ids: [] as string[],
    showTexts: false
  });

  function showResolutionsHistogram() {
    return <ResolutionHistogram
      handleResolutions={(ids: string[]) => setResolutions({ids, showTexts: true})}
      svgRef={svgRef}
    />;
  }

  function showTexts() {
    return <Texts
      resolutions={resolutions.ids}
      handleClose={() => setResolutions({...resolutions, showTexts: false})}
      memoKey={resolutionState.updatedOn}
    />;
  }

  return <div className="row mt-3">
    <div className="col">

      <D3Canvas svgRef={svgRef}/>
      {hasSvg ? showResolutionsHistogram() : null}
      {resolutions.showTexts ? showTexts() : null}

    </div>
  </div>;

}
