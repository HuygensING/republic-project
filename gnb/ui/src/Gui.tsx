import React, {useRef} from 'react';
import GnbElasticClient from "./elastic/GnbElasticClient";
import ContextProvider from "./ContextProvider";
import Version from "./Version";
import {D3Canvas} from "./common/plot/D3Canvas";
import ResolutionViewer from "./resolution/ResolutionViewer";
import ViewComposer from "./view/ViewComposer";
import Views from "./view/Views";
import {Search} from "./search/Search";

type GuiProps = {
  client: GnbElasticClient
}

/**
 * Graphic User Interface
 */
export default function Gui(props: GuiProps) {

  const svgRef = useRef(null);

  return (
    <>
      <div className="gui container-fluid">
        <ContextProvider client={props.client}>
          <div className="row mt-3 mb-3">
            <div className="col">
              <h1>GNB <small className="text-muted">Governance, Netwerken en Besluitvorming in de Staten-Generaal </small></h1>
            </div>
          </div>
          <Search/>
          <ResolutionViewer/>
          <Views/>
          <ViewComposer/>

          <D3Canvas svgRef={svgRef}/>

        </ContextProvider>
      </div>
      <Version />
    </>
  );


}

