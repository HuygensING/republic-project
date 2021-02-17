import {ATTENDANT, MENTIONED, PICK_USER_VIEW, SEARCH_TERM} from "../../Placeholder";
import React, {ChangeEvent} from "react";
import {ViewType} from "../ViewTypes";
import {PersonType} from "../../elastic/model/PersonType";

type SelectViewTypeProps = {
  selected: ViewType | undefined
  selectOption: (e: ChangeEvent<HTMLSelectElement>) => void
}

export default function SelectViewType(props: SelectViewTypeProps) {
  return <div className="form-group">
    <select
      className="form-control"
      id="formControlSelect"
      onChange={props.selectOption}
      value={props.selected ? props.selected : ""}
    >
      <option value="">{PICK_USER_VIEW}</option>
      {createOptions()}
    </select>
  </div>;
}

const ViewTypes = [
  {
    name: PersonType.ATTENDANT,
    personType: PersonType.ATTENDANT,
    placeholder: ATTENDANT
  },
  {
    name: PersonType.MENTIONED,
    personType: PersonType.MENTIONED,
    placeholder: MENTIONED
  },
  {
    name: 'term',
    placeholder: SEARCH_TERM
  }
];

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
