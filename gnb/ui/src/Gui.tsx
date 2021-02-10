import React, {useReducer} from 'react';
import {Search} from "./search/Search";
import {defaultSearchContext, SearchContext, searchReducer} from './search/SearchContext';
import GnbElasticClient from "./elastic/GnbElasticClient";
import ResolutionViewer from "./resolution/ResolutionViewer";
import {defaultResolutionContext, ResolutionContext, resolutionReducer} from './resolution/ResolutionContext';
import UserViews from "./UserViews";
import {defaultPeopleContext, PeopleContext, peopleReducer} from "./person/PeopleContext";

type GuiProps = {
  client: GnbElasticClient
}

/**
 * Graphic User Interface
 */
export default function Gui(props: GuiProps) {

  const [searchState, setSearchState] = useReducer(searchReducer, defaultSearchContext.searchState);
  const [resolutionState, setResolutionState] = useReducer(resolutionReducer, defaultResolutionContext.resolutionState);
  const [peopleState, setPeopleState] = useReducer(peopleReducer, defaultPeopleContext.peopleState);

  return (
    <SearchContext.Provider value={{searchState, setSearchState}}>
      <ResolutionContext.Provider value={{resolutionState, setResolutionState}}>
        <PeopleContext.Provider value={{peopleState, setPeopleState}}>
          <div className="container-fluid">
            <div className="row mt-3 mb-3">
              <div className="col">
                <h1>GNB UI</h1>
              </div>
            </div>

            <Search client={props.client}/>
            <ResolutionViewer client={props.client}/>
            <UserViews client={props.client}/>

          </div>
        </PeopleContext.Provider>
      </ResolutionContext.Provider>
    </SearchContext.Provider>
  );


}

