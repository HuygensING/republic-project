import React, {ChangeEvent, useState} from "react";
import {useSearchContext} from "../SearchContext";
import {WITH_FULL_TEXT} from "../../Placeholder";
import {onEnter} from "../FormUtil";

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

  return <input
      className="form-control"
      value={state.fullText}
      onChange={handleChange}
      type="text"
      placeholder={WITH_FULL_TEXT}
      onBlur={handleSubmit}
      onKeyPress={(e) => onEnter(e, handleSubmit)}
    />;
}
