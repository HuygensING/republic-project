import React, {MutableRefObject, useEffect, useRef, useState} from 'react';
import {Search} from "./search/Search";
import {defaultSearchContext, SearchContext} from './search/SearchContext';
import GnbElasticClient from "./elastic/GnbElasticClient";
import ResolutionsViewer from "./resolution/ResolutionsViewer";
import {D3Canvas} from "./resolution/D3Canvas";

type GuiProps = {
  client: GnbElasticClient
}

/**
 * Graphic User Interface
 */
export default function Gui(props: GuiProps) {

  const [state, setState] = React.useState(defaultSearchContext.state);

  const context = {
    state, setState
  };

  return (
    <SearchContext.Provider value={context}>
      <div className="container-fluid">
        <div className="row mt-3 mb-3">
          <div className="col">
            <h1>GNB UI</h1>
          </div>
        </div>

        <Search client={props.client}/>
        <ResolutionsViewer client={props.client} />
      </div>
    </SearchContext.Provider>
  );


}

