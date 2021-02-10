import React, {MutableRefObject, useEffect, useRef, useState} from "react";
import ResolutionHistogram from "./ResolutionHistogram";
import TextsModal from "../common/Texts";
import {D3Canvas} from "../common/D3Canvas";

export default function ResolutionViewer() {

  const svgRef: MutableRefObject<any> = useRef(null);

  const [hasSvg, setHasSvg] = useState(svgRef.current);

  useEffect(() => {
    setHasSvg(svgRef.current)
  }, [svgRef]);

  const [resolutions, setResolutions] = React.useState({
    ids: [] as string[],
    showTexts: false
  });

  function renderBarchart() {
    return <ResolutionHistogram
      handleResolutions={(ids: string[]) => setResolutions({ids, showTexts: true})}
      svgRef={svgRef}
    />;
  }

  return <div className="row mt-3">
    <div className="col">
      <D3Canvas svgRef={svgRef}/>
      {hasSvg ? renderBarchart() : null}
      <TextsModal
        resolutions={resolutions.ids}
        isOpen={resolutions.showTexts}
        handleClose={() => setResolutions({...resolutions, showTexts: false})}
      />
    </div>
  </div>;

}
