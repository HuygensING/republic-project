import PeopleTypeahead from "../search/field/PeopleTypeahead";
import React from "react";
import {PersonType} from "../elastic/model/PersonType";
import {PersonOption} from "../search/PersonOption";
import {PICK_MENTIONED} from "../Placeholder";

type AddMentionedViewTypeaheadProps = {
  handleSubmit: (o: PersonOption, t: PersonType) => Promise<void>
}

export default function AddMentionedViewTypeahead(props: AddMentionedViewTypeaheadProps) {
  return <PeopleTypeahead
    placeholder={PICK_MENTIONED}
    personType={PersonType.MENTIONED}
    handleSubmit={(o) => props.handleSubmit(o[0], PersonType.MENTIONED)}
    id="mentioned-typeahead"
  />;
}
