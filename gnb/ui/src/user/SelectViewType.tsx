import {PICK_USER_VIEW} from "../Placeholder";
import React, {ChangeEvent} from "react";
import {ViewType, ViewTypes} from "./ViewTypes";

type SelectViewTypeProps = {
  selected: ViewType | null
  selectOption: (e: ChangeEvent<HTMLSelectElement>) => void
}

export default function SelectViewType(props: SelectViewTypeProps) {
  return <div className="form-group">
    <select
      className="form-control"
      id="formControlSelect"
      onChange={props.selectOption}
      value={props.selected ? props.selected.type : ""}
    >
      <option value="">{PICK_USER_VIEW}</option>
      {createOptions()}
    </select>
  </div>;
}

function createOptions() {
  return ViewTypes.map((type, index) => {
    return <option
      key={index}
      value={type.type}
    >
      {type.placeholder}
    </option>
  });
}
