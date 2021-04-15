import React from "react";
import {useSearchContext} from "../SearchContext";
import {HELP_BALLOON_FUNCTIONS, WITH_FUNCTIONS} from "../../content/Placeholder";
import FunctionTypeahead, {FunctionOption} from "../../common/form/FunctionTypeahead";

export default function FunctionFormField() {

  const {searchState, setSearchState} = useSearchContext();

  const handleSubmit = async (selected: FunctionOption[]) => {
    const functions = selected.map(s => s.personFunction);
    setSearchState({...searchState, functions});
  };

  return <div aria-label={HELP_BALLOON_FUNCTIONS} data-balloon-pos="down">
    <FunctionTypeahead
      placeholder={WITH_FUNCTIONS}
      handleSubmit={handleSubmit}
      id="functions-typeahead"
    />
  </div>;
}
