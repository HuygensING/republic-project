import {createContext, useContext} from 'react';
import {BaseStateType, reducer} from "../BaseStateType";
import GnbElasticClient from "./GnbElasticClient";

export type ClientStateType = BaseStateType & {
  client: GnbElasticClient;
}

export type ClientContextType = {
  clientState: ClientStateType;
  setClientState: (s: ClientStateType) => void
}

export const ClientContext = createContext<ClientContextType>({} as unknown as ClientContextType);

export const useClientContext = () => useContext(ClientContext);

export const clientReducer : (<T extends ClientStateType>(s: T, a: T) => T) = reducer;
