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

  function renderHistogram() {
    return <ResolutionHistogram
      handleResolutions={(ids: string[]) => setResolutions({ids, showTexts: true})}
      svgRef={svgRef}
    />;
  }

  function renderTexts() {
    return <Texts
      resolutions={resolutions.ids}
      handleClose={() => setResolutions({...resolutions, showTexts: false})}
      memoKey={resolutionState.updatedOn}
    />;
  }

  return <div className="row mt-3">
    <div className="col row-view">

      <D3Canvas svgRef={svgRef}/>
      {
        hasSvg
          ? renderHistogram()
          : null
      }
      {resolutions.showTexts
        ? renderTexts()
        : null
      }

    </div>
  </div>;

}
