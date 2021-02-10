import React, {useReducer} from 'react';
import {Search} from "./search/Search";
import {defaultSearchContext, SearchContext} from './search/SearchContext';
import GnbElasticClient from "./elastic/GnbElasticClient";
import ResolutionViewer from "./resolution/ResolutionViewer";
import {defaultResolutionContext, ResolutionContext, ResolutionStateType} from './resolution/ResolutionContext';
import UserViews from "./UserViews";
import {defaultPeopleContext, PeopleContext} from "./person/PeopleContext";
import {Action, ActionType} from "./BaseStateType";

type GuiProps = {
  client: GnbElasticClient
}

function reducer(state: ResolutionStateType, action: Action<ResolutionStateType>) : ResolutionStateType {
  console.log('reduce?', state, action);

  switch (action.type) {
    case ActionType.UPDATE:
      action.payload.updatedOn = new Date().getTime();
      return action.payload;
    default:
      return action.payload;
  }
}

/**
 * Graphic User Interface
 */
export default function Gui(props: GuiProps) {

  const [searchState, setSearchState] = React.useState(defaultSearchContext.searchState);
  const [resolutionState, setResolutionState] = useReducer(reducer, defaultResolutionContext.resolutionState);
  const [peopleState, setPeopleState] = React.useState(defaultPeopleContext.peopleState);

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

