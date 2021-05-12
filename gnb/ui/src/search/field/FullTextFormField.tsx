import React, {ChangeEvent, useState} from "react";
import {useSearchContext} from "../SearchContext";
import {HELP_BALLOON_SEARCH_TERMS, WITH_FULL_TEXT} from "../../content/Placeholder";
import {onEnter} from "../../util/onEnter";

const xmlKeywords = [
  "bibliografie",
  "deel",
  "instelling",
  "literatuur",
  "formeel",
  "idnr",
  "naam",
  "noot",
  "p",
  "persoon",
  "plaats",
  "postprandium",
  "presentielijst",
  "prespersoon",
  "provincie",
  "resolutie",
  "scheepsnaam",
  "status",
  "variant",
  "zittingsdag"
];

export default function FullTextFormField() {

  const {searchState, setSearchState} = useSearchContext();

  const [state, setState] = useState({
    fullText: searchState.fullText,
    error: ''
  });

  const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
    setState({...state, fullText: e.target.value});
  };

  const handleSubmit = () => {
    if (xmlKeywords.includes(state.fullText)) {
      setState({
        ...state,
        error: `Cannot search on '${state.fullText}' (source xml uses '${state.fullText}' as an element or attribute name)`
      });
    } else {
      setSearchState({...searchState, fullText: state.fullText});
    }
  };

  /**
   * Throw error or render component
   */
  function render() {
    if (state.error) {
      throw new Error(state.error);
    }
    return <div aria-label={HELP_BALLOON_SEARCH_TERMS} data-balloon-pos="down">
      <input
        className="form-control"
        value={state.fullText}
        onChange={handleChange}
        type="text"
        placeholder={WITH_FULL_TEXT}
        onBlur={handleSubmit}
        onKeyPress={(e) => onEnter(e, handleSubmit)}
      /></div>;
  }

  return render();
}
