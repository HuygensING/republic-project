import React, {ChangeEvent, useState} from "react";
import {useSearchContext} from "../SearchContext";
import {HELP_BALLOON_SEARCH_TERMS, WITH_FULL_TEXT} from "../../content/Placeholder";
import {onEnter} from "../../util/onEnter";

export default function FullTextFormField() {

  const {searchState, setSearchState} = useSearchContext();

  const [state, setState] = useState({
    fullText: searchState.fullText
  });

  const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
    setState({...state, fullText: e.target.value});
  };

  const handleSubmit = () => {
    setSearchState({...searchState, fullText: state.fullText});
  };

  return <div aria-label={HELP_BALLOON_SEARCH_TERMS} data-balloon-pos="down">
    <input
      className="form-control"
      value={state.fullText}
      onChange={handleChange}
      type="text"
      placeholder={WITH_FULL_TEXT}
      onBlur={handleSubmit}
      onKeyPress={(e) => onEnter(e, handleSubmit)}
    /></div>
}
