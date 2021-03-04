import React from "react";
import {ViewType} from "../model/ViewType";
import {PICK_FUNCTION} from "../../content/Placeholder";
import {PersonFunction} from "../../elastic/model/PersonFunction";
import FunctionTypeahead from "../../common/FunctionTypeahead";

type AddFunctionViewTypeaheadProps = {
  handleSubmit: (l: PersonFunction, t: ViewType) => Promise<void>
}

export default function AddFunctionViewTypeahead(props: AddFunctionViewTypeaheadProps) {

  return <FunctionTypeahead
    placeholder={PICK_FUNCTION}
    handleSubmit={(o: any) => props.handleSubmit({name: o[0].name} as PersonFunction, ViewType.FUNCTION)}
    id="add-place-view-typeahead"
  />
}
