import PeopleTypeahead from "../../search/field/PeopleTypeahead";
import React from "react";
import {PersonType} from "../../elastic/model/PersonType";
import {PersonOption} from "../../search/PersonOption";
import {PICK_MENTIONED} from "../../Placeholder";
import {ViewType, ViewTypes} from "../ViewTypes";

type AddMentionedViewTypeaheadProps = {
  handleSubmit: (o: PersonOption, t: ViewType) => Promise<void>
}

export default function AddMentionedViewTypeahead(props: AddMentionedViewTypeaheadProps) {
  return <PeopleTypeahead
    placeholder={PICK_MENTIONED}
    personType={PersonType.MENTIONED}
    handleSubmit={(o) => props.handleSubmit(o[0], ViewType.MENTIONED)}
    id="mentioned-typeahead"
  />;
}
