import {createContext, useContext} from 'react';
import {Person} from "../elastic/model/Person";
import {BaseStateType, defaultBaseContext, dummy, reducer} from "../BaseStateType";
import Place from "../view/model/Place";
import {PersonFunction} from "../elastic/model/PersonFunction";
import {PersonFunctionCategory} from "../elastic/model/PersonFunctionCategory";

export type SearchStateType = BaseStateType & {
  attendants: Person[];
  mentioned: Person[];
  fullText: string;
  places: Place[];
  start: Date;
  end: Date;
  functions: PersonFunction[];
  functionCategories: PersonFunctionCategory[];
}

export type SearchContextType = {
  searchState: SearchStateType;
  setSearchState: (s: SearchStateType) => void
}

export const defaultSearchContext = {
  searchState: {
    ...defaultBaseContext,
    attendants: [],
    mentioned: [],
    fullText: '',
    places: [],
    start: new Date('1626-01-01'),
    end: new Date('1626-06-30'),
    functions: [],
    functionCategories: []
  },
  setSearchState: dummy
} as SearchContextType;

export const SearchContext = createContext<SearchContextType>(defaultSearchContext);

export const useSearchContext = () => useContext(SearchContext);

export const searchReducer : (<T extends SearchStateType>(s: T, a: T) => T) = reducer;
