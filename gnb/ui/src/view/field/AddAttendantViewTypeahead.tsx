import PeopleTypeahead from "../../search/field/PeopleTypeahead";
import React from "react";
import {PersonType} from "../../elastic/model/PersonType";
import {PersonOption} from "../../search/PersonOption";
import {PICK_ATTENDANT} from "../../Placeholder";
import {ViewType, ViewTypes} from "../ViewTypes";

type AddAttendantViewTypeaheadProps = {
  handleSubmit: (o: PersonOption, t: ViewType) => Promise<void>
}

export default function AddAttendantViewTypeahead (props: AddAttendantViewTypeaheadProps) {
  return <PeopleTypeahead
    placeholder={PICK_ATTENDANT}
    personType={PersonType.ATTENDANT}
    handleSubmit={(o) => props.handleSubmit(o[0], ViewType.ATTENDANT)}
    id="attendant-typeahead"
  />;
}