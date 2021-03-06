import PeopleTypeahead from "../../common/form/PeopleTypeahead";
import React from "react";
import {PersonType} from "../../elastic/model/PersonType";
import {PICK_MENTIONED} from "../../content/Placeholder";
import {ViewType} from "../model/ViewType";
import {Person} from "../../elastic/model/Person";

type AddMentionedViewTypeaheadProps = {
  handleSubmit: (o: Person, t: ViewType) => Promise<void>
}

export default function AddMentionedViewTypeahead(props: AddMentionedViewTypeaheadProps) {
  return <PeopleTypeahead
    placeholder={PICK_MENTIONED}
    personType={PersonType.MENTIONED}
    handleSubmit={(o) => props.handleSubmit(o[0].person, ViewType.MENTIONED)}
    id="add-mentioned-typeahead"
  />;
}
