import React from "react";

import 'react-bootstrap-typeahead/css/Typeahead.css';
import GnbElasticClient from "../../elastic/GnbElasticClient";
import PeopleTypeahead from "./PeopleTypeahead";
import {WITH_ATTENDANTS} from "../../Placeholder";
import {PersonType} from "../../elastic/model/PersonType";
import {PersonOption} from "../PersonOption";
import {useSearchContext} from "../SearchContext";

type AttendantsFormFieldProps = {
  client: GnbElasticClient
};

export default function AttendantsFormField(props: AttendantsFormFieldProps) {

  const {state, setState} = useSearchContext();

  const handleSubmit = async (selected: PersonOption[]) => {
    setState({...state, attendants: selected.map(s => s.person)});
  };

  return <div className="form-group">
    <PeopleTypeahead
      client={props.client}
      placeholder={WITH_ATTENDANTS}
      personType={PersonType.ATTENDANT}
      handleSubmit={handleSubmit}
      id="attendants-typeahead"
    />
  </div>;
}


