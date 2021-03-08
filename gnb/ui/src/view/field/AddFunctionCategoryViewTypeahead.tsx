import React from "react";
import {ViewType} from "../model/ViewType";
import {PICK_FUNCTION_CATEGORY} from "../../content/Placeholder";
import FunctionCategoryTypeahead, {FunctionCategoryOption} from "../../common/form/FunctionCategoryTypeahead";
import {PersonFunctionCategory} from "../../elastic/model/PersonFunctionCategory";

type AddFunctionCategoryViewTypeaheadProps = {
  handleSubmit: (l: PersonFunctionCategory, t: ViewType) => Promise<void>
}

export default function AddFunctionCategoryViewTypeahead(props: AddFunctionCategoryViewTypeaheadProps) {

  return <FunctionCategoryTypeahead
    placeholder={PICK_FUNCTION_CATEGORY}
    handleSubmit={(o: FunctionCategoryOption[]) => {
      return props.handleSubmit(o[0].personFunctionCategory, ViewType.FUNCTION_CATEGORY);
    }}
    id="add-function-category-view-typeahead"
  />
}
