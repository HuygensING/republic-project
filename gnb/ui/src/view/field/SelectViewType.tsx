import {ATTENDANT, LOCATION, MENTIONED, PICK_USER_VIEW} from "../../Placeholder";
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
    name: PersonType.ATTENDANT,
    placeholder: ATTENDANT
  },
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
    name: ViewType.LOCATION,
    placeholder: LOCATION
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
