import React, {MutableRefObject, useEffect, useRef, useState} from "react";
import ResolutionPlot from "./ResolutionPlot";
import {D3Canvas} from "../common/plot/D3Canvas";
import {Texts} from "../common/texts/Texts";
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

  function renderPlot() {
    return <ResolutionPlot
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
          ? renderPlot()
          : null
      }
      {resolutions.showTexts
        ? renderTexts()
        : null
      }

    </div>
  </div>;

}
