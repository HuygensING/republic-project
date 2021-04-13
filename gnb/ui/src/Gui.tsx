import React from 'react';
import {Search} from "./search/Search";
import GnbElasticClient from "./elastic/GnbElasticClient";
import ResolutionViewer from "./resolution/ResolutionViewer";
import Views from "./view/Views";
import ContextProvider from "./ContextProvider";
import ViewComposer from "./view/ViewComposer";
import Version from "./Version";

type GuiProps = {
  client: GnbElasticClient
}

/**
 * Graphic User Interface
 */
export default function Gui(props: GuiProps) {

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
        </ContextProvider>
      </div>
      <Version />
    </>
  );


}

