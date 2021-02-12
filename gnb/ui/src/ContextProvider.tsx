import {ClientContext, clientReducer, ClientStateType} from "./search/ClientContext";
import {defaultSearchContext, SearchContext, searchReducer} from "./search/SearchContext";
import {defaultResolutionContext, ResolutionContext, resolutionReducer} from "./resolution/ResolutionContext";
import React, {useReducer} from "react";
import GnbElasticClient from "./elastic/GnbElasticClient";
import {defaultViewContext, viewReducer, ViewContext} from "./view/ViewContext";

interface ContextProviderProps {
  client: GnbElasticClient
  children: React.ReactNode;
}

export default function ContextProvider(props: ContextProviderProps) {

  const defaultClientState = {client: props.client} as ClientStateType;
  const [clientState, setClientState] = useReducer(clientReducer, defaultClientState);

  const [searchState, setSearchState] = useReducer(searchReducer, defaultSearchContext.searchState);
  const [resolutionState, setResolutionState] = useReducer(resolutionReducer, defaultResolutionContext.resolutionState);
  const [viewState, setViewState] = useReducer(viewReducer, defaultViewContext.viewState);

  return <>
    <ClientContext.Provider value={{clientState, setClientState}}>
      <SearchContext.Provider value={{searchState, setSearchState}}>
        <ResolutionContext.Provider value={{resolutionState, setResolutionState}}>
          <ViewContext.Provider value={{viewState, setViewState}}>
            {props.children}
          </ViewContext.Provider>
        </ResolutionContext.Provider>
      </SearchContext.Provider>
    </ClientContext.Provider>
  </>
}