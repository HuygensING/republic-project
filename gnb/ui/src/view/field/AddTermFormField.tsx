import React, {useState} from "react";
import {WITH_FULL_TEXT} from "../../content/Placeholder";
import {ViewType} from "../model/ViewType";
import {onEnter} from "../../search/FormUtil";
import {Term} from "../model/Term";

type AddTermFormFieldProps = {
  handleSubmit: (o: Term, t: ViewType) => Promise<void>
}

export default function AddTermFormField(props: AddTermFormFieldProps) {

  const [state, setState] = useState({
    fullText: ''
  });

  function handleSubmit() {
    return props.handleSubmit(new Term(state.fullText), ViewType.TERM);
  }

  return <div className="input-group">
    <input
      className="form-control"
      value={state.fullText}
      onChange={(e) => setState({...state, fullText: e.target.value})}
      type="text"
      placeholder={WITH_FULL_TEXT}
      onBlur={handleSubmit}
      onKeyPress={(e) => onEnter(e, handleSubmit)}
    />
    <div className="input-group-append">
      <button
        type="button"
        className="btn btn-outline-secondary"
        onClick={handleSubmit}
      >
        &gt;&gt;
      </button>
    </div>

  </div>;
}
