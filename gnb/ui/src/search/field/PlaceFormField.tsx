import React from "react";
import {useSearchContext} from "../SearchContext";
import {HELP_BALLOON_PLACES, WITH_PLACES} from "../../content/Placeholder";
import PlaceTypeahead, {PlaceOption} from "../../common/form/PlaceTypeahead";
import Place from "../../view/model/Place";

export default function PlaceFormField() {

  const {searchState, setSearchState} = useSearchContext();

  const handleSubmit = async (selected: PlaceOption[]) => {
    setSearchState({...searchState, places: selected.map(s => new Place(s.name))});
  };

  return <div aria-label={HELP_BALLOON_PLACES} data-balloon-pos="down">
    <PlaceTypeahead
      placeholder={WITH_PLACES}
      handleSubmit={handleSubmit}
      id="places-typeahead"
    />
  </div>;
}
