import React from "react";
import {useSearchContext} from "../SearchContext";
import {WITH_PLACES} from "../../Placeholder";
import PlaceTypeahead, {PlaceOption} from "../../common/PlaceTypeahead";
import Place from "../../view/model/Place";

export default function PlaceFormField() {

  const {searchState, setSearchState} = useSearchContext();

  const handleSubmit = async (selected: PlaceOption[]) => {
    setSearchState({...searchState, places: selected.map(s => new Place(s.name))});
  };

  return <div>
    <PlaceTypeahead
      placeholder={WITH_PLACES}
      handleSubmit={handleSubmit}
      id="mentioned-typeahead"
    />
  </div>;
}
