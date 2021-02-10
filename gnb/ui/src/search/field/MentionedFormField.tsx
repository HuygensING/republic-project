import React from "react";
import {useSearchContext} from "../SearchContext";
import {WITH_MENTIONED} from "../../Placeholder";
import PeopleTypeahead from "./PeopleTypeahead";
import {PersonType} from "../../elastic/model/PersonType";
import {PersonOption} from "../PersonOption";

export default function MentionedFormField() {

  const {searchState, setSearchState} = useSearchContext();

  const handleSubmit = async (selected: PersonOption[]) => {
    setSearchState({...searchState, mentioned: selected.map(s => s.person)});
  };

  return <div>
    <PeopleTypeahead
      placeholder={WITH_MENTIONED}
      personType={PersonType.MENTIONED}
      handleSubmit={handleSubmit}
      id="mentioned-typeahead"
    />
  </div>;
}
