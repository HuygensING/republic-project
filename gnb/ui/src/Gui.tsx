import React from 'react';
import {Search} from "./search/Search";
import {defaultSearchContext, SearchContext} from './search/SearchContext';
import GnbElasticClient from "./elastic/GnbElasticClient";
import ResolutionViewer from "./resolution/ResolutionViewer";
import PersonViewer from "./person/PersonViewer";
import {defaultResolutionContext, ResolutionContext} from './resolution/ResolutionContext';
import {PersonContext} from './person/PersonContext';
import {defaultPersonContext} from "./person/PersonContext";

type GuiProps = {
  client: GnbElasticClient
}

/**
 * Graphic User Interface
 */
export default function Gui(props: GuiProps) {

  const [searchState, setSearchState] = React.useState(defaultSearchContext.searchState);
  const [resolutionState, setResolutionState] = React.useState(defaultResolutionContext.resolutionState);
  const [personState, setPersonState] = React.useState(defaultPersonContext.personState);
  return (
    <SearchContext.Provider value={{searchState, setSearchState}}>
      <div className="container-fluid">
        <div className="row mt-3 mb-3">
          <div className="col">
            <h1>GNB UI</h1>
          </div>
        </div>

        <Search client={props.client}/>

        <ResolutionContext.Provider value={{resolutionState, setResolutionState}}>
          <ResolutionViewer client={props.client} />
          <PersonContext.Provider value={{personState, setPersonState}}>
            <PersonViewer client={props.client} />
          </PersonContext.Provider>
        </ResolutionContext.Provider>

      </div>
    </SearchContext.Provider>
  );


}

