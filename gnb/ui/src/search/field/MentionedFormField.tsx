import React from "react";
import {useSearchContext} from "../SearchContext";
import {WITH_MENTIONED} from "../../Placeholder";
import PeopleTypeahead from "./PeopleTypeahead";
import {PersonType} from "../../elastic/model/PersonType";
import {PersonOption} from "../PersonOption";
import GnbElasticClient from "../../elastic/GnbElasticClient";

type MentionedFormFieldProps = {
  client: GnbElasticClient
};

export default function MentionedFormField(props: MentionedFormFieldProps) {

  const {state, setState} = useSearchContext();

  const handleSubmit = async (selected: PersonOption[]) => {
    setState({...state, mentioned: selected.map(s => s.person)});
  };

  return <div>
    <PeopleTypeahead
      client={props.client}
      placeholder={WITH_MENTIONED}
      personType={PersonType.MENTIONED}
      handleSubmit={handleSubmit}
      id="mentioned-typeahead"
    />
  </div>;
}
