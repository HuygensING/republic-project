import PeopleTypeahead from "../../common/PeopleTypeahead";
import React from "react";
import {PersonType} from "../../elastic/model/PersonType";
import {PICK_ATTENDANT} from "../../Placeholder";
import {ViewType} from "../model/ViewType";
import {Person} from "../../elastic/model/Person";

type AddAttendantViewTypeaheadProps = {
  handleSubmit: (o: Person, t: ViewType) => Promise<void>
}

export default function AddAttendantViewTypeahead (props: AddAttendantViewTypeaheadProps) {
  return <PeopleTypeahead
    placeholder={PICK_ATTENDANT}
    personType={PersonType.ATTENDANT}
    handleSubmit={(o) => props.handleSubmit(o[0].person, ViewType.ATTENDANT)}
    id="attendant-typeahead"
  />;
}
