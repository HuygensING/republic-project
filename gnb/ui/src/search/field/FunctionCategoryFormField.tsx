import React from "react";
import {useSearchContext} from "../SearchContext";
import {HELP_BALLOON_FUNCTION_CATEGORIES, WITH_FUNCTION_CATEGORIES} from "../../content/Placeholder";
import FunctionCategoryTypeahead, {FunctionCategoryOption} from "../../common/form/FunctionCategoryTypeahead";

export default function FunctionCategoryFormField() {

  const {searchState, setSearchState} = useSearchContext();

  const handleSubmit = async (selected: FunctionCategoryOption[]) => {
    const functionCategories = selected.map(s => s.personFunctionCategory);
    setSearchState({...searchState, functionCategories});
  };

  return <div aria-label={HELP_BALLOON_FUNCTION_CATEGORIES} data-balloon-pos="down">
    <FunctionCategoryTypeahead
      placeholder={WITH_FUNCTION_CATEGORIES}
      handleSubmit={handleSubmit}
      id="functions-typeahead"
    />
  </div>;
}
