import React from "react";

import 'react-bootstrap-typeahead/css/Typeahead.css';
import PeopleTypeahead, {PersonOption} from "../../common/PeopleTypeahead";
import {WITH_ATTENDANTS} from "../../content/Placeholder";
import {PersonType} from "../../elastic/model/PersonType";
import {useSearchContext} from "../SearchContext";

export default function AttendantsFormField() {

  const {searchState, setSearchState} = useSearchContext();

  const handleSubmit = async (selected: PersonOption[]) => {
    setSearchState({...searchState, attendants: selected.map(s => s.person)});
  };

  return <PeopleTypeahead
    placeholder={WITH_ATTENDANTS}
    personType={PersonType.ATTENDANT}
    handleSubmit={handleSubmit}
    id="attendants-typeahead"
  />;
}


