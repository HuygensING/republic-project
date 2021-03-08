import React from "react";
import {ViewType} from "../model/ViewType";
import {PICK_FUNCTION} from "../../content/Placeholder";
import {PersonFunction} from "../../elastic/model/PersonFunction";
import FunctionTypeahead, {FunctionOption} from "../../common/form/FunctionTypeahead";

type AddFunctionViewTypeaheadProps = {
  handleSubmit: (l: PersonFunction, t: ViewType) => Promise<void>
}

export default function AddFunctionViewTypeahead(props: AddFunctionViewTypeaheadProps) {

  return <FunctionTypeahead
    placeholder={PICK_FUNCTION}
    handleSubmit={(o: FunctionOption[]) => {
      return props.handleSubmit(o[0].personFunction, ViewType.FUNCTION);
    }}
    id="add-function-view-typeahead"
  />
}
