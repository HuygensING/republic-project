import React from 'react';
import {Search} from "./search/Search";
import GnbElasticClient from "./elastic/GnbElasticClient";
import ResolutionViewer from "./resolution/ResolutionViewer";
import UserViews from "./UserViews";
import ContextProvider from "./ContextProvider";

type GuiProps = {
  client: GnbElasticClient
}

/**
 * Graphic User Interface
 */
export default function Gui(props: GuiProps) {

  return (
    <ContextProvider client={props.client}>
      <div className="container-fluid">

        <div className="row mt-3 mb-3">
          <div className="col">
            <h1>GNB UI</h1>
          </div>
        </div>

        <Search/>
        <ResolutionViewer/>
        <UserViews/>
      </div>
    </ContextProvider>
  );


}

