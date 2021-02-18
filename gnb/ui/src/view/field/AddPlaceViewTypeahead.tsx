import React from "react";
import Place from "../model/Place";
import {ViewType} from "../model/ViewType";
import {PICK_PLACE} from "../../content/Placeholder";
import PlaceTypeahead from "../../common/PlaceTypeahead";

type AddPlaceViewTypeaheadProps = {
  handleSubmit: (l: Place, t: ViewType) => Promise<void>
}

export default function AddPlaceViewTypeahead(props: AddPlaceViewTypeaheadProps) {

  return <PlaceTypeahead
    placeholder={PICK_PLACE}
    handleSubmit={(o) => props.handleSubmit(new Place(o[0].name), ViewType.PLACE)}
    id="add-place-view-typeahead"
  />
}
