import React from 'react';
import {Search} from "./search/Search";
import {defaultSearchContext, SearchContext} from './search/SearchContext';
import GnbElasticClient from "./elastic/GnbElasticClient";
import ResolutionViewer from "./resolution/ResolutionViewer";
import PeopleViewer from "./people/PeopleViewer";
import {defaultResolutionContext, ResolutionContext} from './resolution/ResolutionContext';

type GuiProps = {
  client: GnbElasticClient
}

/**
 * Graphic User Interface
 */
export default function Gui(props: GuiProps) {

  const [searchState, setSearchState] = React.useState(defaultSearchContext.searchState);
  const searchContext = {
    searchState, setSearchState
  };

  const [resolutionState, setResolutionState] = React.useState(defaultResolutionContext.resolutionState);
  const resolutionContext = {
    resolutionState, setResolutionState
  };

  return (
    <SearchContext.Provider value={searchContext}>
      <div className="container-fluid">
        <div className="row mt-3 mb-3">
          <div className="col">
            <h1>GNB UI</h1>
          </div>
        </div>

        <Search client={props.client}/>

        <ResolutionContext.Provider value={resolutionContext}>
          <ResolutionViewer client={props.client} />
          <PeopleViewer client={props.client} />
        </ResolutionContext.Provider>

      </div>
    </SearchContext.Provider>
  );


}

