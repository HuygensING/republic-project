import {ATTENDANT, FUNCTION, MENTIONED, PICK_USER_VIEW, PLACE, TERM} from "../../content/Placeholder";
import React, {ChangeEvent} from "react";
import {ViewType} from "../model/ViewType";
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

export const ViewTypes = [
  {
    name: ViewType.ATTENDANT,
    personType: PersonType.ATTENDANT,
    placeholder: ATTENDANT
  },
  {
    name: ViewType.MENTIONED,
    personType: PersonType.MENTIONED,
    placeholder: MENTIONED
  },
  {
    name: ViewType.TERM,
    placeholder: TERM
  },
  {
    name: ViewType.FUNCTION,
    placeholder: PLACE
  },
  {
    name: ViewType.PLACE,
    placeholder: PLACE
  },
  {
    name: ViewType.FUNCTION,
    placeholder: FUNCTION
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
