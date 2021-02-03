import React, {ChangeEvent, useState} from "react";
import {useSearchContext} from "../SearchContext";
import {WITH_FULL_TEXT} from "../../Placeholder";
import {onEnter} from "../FormUtil";

export default function FullTextFormField() {

  const {state, setState} = useSearchContext();

  const [searchState, setSearchState] = useState({
    fullText: state.fullText
  });

  const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
    setSearchState({...searchState, fullText: e.target.value});
  };

  const handleSubmit = () => {
    setState({...state, fullText: searchState.fullText});
  };

  return <input
      className="form-control"
      value={searchState.fullText}
      onChange={handleChange}
      type="text"
      placeholder={WITH_FULL_TEXT}
      onBlur={handleSubmit}
      onKeyPress={(e) => onEnter(e, handleSubmit)}
    />;
}
