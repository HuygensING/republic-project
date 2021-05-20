import {ClientContext, clientReducer, ClientStateType} from "./elastic/ClientContext";
import {defaultSearchContext, SearchContext, searchReducer} from "./search/SearchContext";
import {defaultResolutionContext, ResolutionContext, resolutionReducer} from "./resolution/ResolutionContext";
import React, {useReducer} from "react";
import GnbElasticClient from "./elastic/GnbElasticClient";
import {defaultViewContext, ViewContext, viewReducer} from "./view/ViewContext";
import {defaultPlotContext, PlotContext, plotReducer} from "./common/plot/PlotContext";
import {defaultLoadingContext, LoadingContext, loadingReducer} from "./LoadingContext";

interface ContextProviderProps {
  client: GnbElasticClient
  children: React.ReactNode;
}

export default function ContextProvider(props: ContextProviderProps) {

  const defaultClientState = {client: props.client} as ClientStateType;
  const [clientState, setClientState] = useReducer(clientReducer, defaultClientState);
  const [loadingState, setLoadingState] = useReducer(loadingReducer, defaultLoadingContext.loadingState);
  const [plotState, setPlotState] = useReducer(plotReducer, defaultPlotContext.plotState);

  const [searchState, setSearchState] = useReducer(searchReducer, defaultSearchContext.searchState);
  const [resolutionState, setResolutionState] = useReducer(resolutionReducer, defaultResolutionContext.resolutionState);
  const [viewState, setViewState] = useReducer(viewReducer, defaultViewContext.viewState);

  return <>
    <ClientContext.Provider value={{clientState, setClientState}}>
      <LoadingContext.Provider value={{loadingState, setLoadingState}}>
        <PlotContext.Provider value={{plotState, setPlotState}}>
          <SearchContext.Provider value={{searchState, setSearchState}}>
            <ResolutionContext.Provider value={{resolutionState, setResolutionState}}>
              <ViewContext.Provider value={{viewState, setViewState}}>
                {props.children}
              </ViewContext.Provider>
            </ResolutionContext.Provider>
          </SearchContext.Provider>
        </PlotContext.Provider>
      </LoadingContext.Provider>
    </ClientContext.Provider>
  </>
}
