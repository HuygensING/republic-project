import {PICK_USER_VIEW} from "../../Placeholder";
import React, {ChangeEvent} from "react";
import {ViewType, ViewTypes} from "../ViewTypes";

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
      value={props.selected ? props.selected.name : ""}
    >
      <option value="">{PICK_USER_VIEW}</option>
      {createOptions()}
    </select>
  </div>;
}

function createOptions() {
  return Object.entries(ViewTypes).map(([name, value]) => {
    return <option
      key={name}
      value={value.name}
    >
      {value.placeholder}
    </option>
  });
}
