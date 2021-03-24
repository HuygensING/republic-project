import React from "react";
import {useSearchContext} from "../SearchContext";
import {HELP_BALLOON_MENTIONED, WITH_MENTIONED} from "../../content/Placeholder";
import PeopleTypeahead, {PersonOption} from "../../common/form/PeopleTypeahead";
import {PersonType} from "../../elastic/model/PersonType";

export default function MentionedFormField() {

  const {searchState, setSearchState} = useSearchContext();

  const handleSubmit = async (selected: PersonOption[]) => {
    setSearchState({...searchState, mentioned: selected.map(s => s.person)});
  };

  return <div aria-label={HELP_BALLOON_MENTIONED} data-balloon-pos="down">
    <PeopleTypeahead
      placeholder={WITH_MENTIONED}
      personType={PersonType.MENTIONED}
      handleSubmit={handleSubmit}
      id="mentioned-typeahead"
    />
  </div>;
}
