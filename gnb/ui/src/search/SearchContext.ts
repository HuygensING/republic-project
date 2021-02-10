import {createContext, useContext} from 'react';
import {Person} from "../elastic/model/Person";
import {BaseStateType, defaultBaseContext, dummy, reducer} from "../BaseStateType";
import {ResolutionStateType} from "../resolution/ResolutionContext";

export type SearchStateType = BaseStateType & {
  attendants: Person[];
  mentioned: Person[];
  fullText: string;
  start: Date;
  end: Date;
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
    start: new Date('1630-01-01'),
    end: new Date('1630-01-30'),
  },
  setSearchState: dummy
} as SearchContextType;

export const SearchContext = createContext<SearchContextType>(defaultSearchContext);

export const useSearchContext = () => useContext(SearchContext);

export const searchReducer : (<T extends SearchStateType>(s: T, a: T) => T) = reducer;
