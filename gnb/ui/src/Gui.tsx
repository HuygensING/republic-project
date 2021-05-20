import React from 'react';
import GnbElasticClient from "./elastic/GnbElasticClient";
import ContextProvider from "./ContextProvider";
import Version from "./Version";
import ResolutionViewer from "./resolution/ResolutionViewer";
import ViewComposer from "./view/ViewComposer";
import Views from "./view/Views";
import {Search} from "./search/Search";
import {Header} from "./Header";

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
          <Header />
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

