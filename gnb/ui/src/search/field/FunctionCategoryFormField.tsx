import React from "react";
import {useSearchContext} from "../SearchContext";
import {WITH_FUNCTION_CATEGORIES} from "../../content/Placeholder";
import FunctionCategoryTypeahead, {FunctionCategoryOption} from "../../common/form/FunctionCategoryTypeahead";

export default function FunctionCategoryFormField() {

  const {searchState, setSearchState} = useSearchContext();

  const handleSubmit = async (selected: FunctionCategoryOption[]) => {
    const functionCategories = selected.map(s => s.personFunctionCategory);
    setSearchState({...searchState, functionCategories});
  };

  return <div>
    <FunctionCategoryTypeahead
      placeholder={WITH_FUNCTION_CATEGORIES}
      handleSubmit={handleSubmit}
      id="functions-typeahead"
    />
  </div>;
}
