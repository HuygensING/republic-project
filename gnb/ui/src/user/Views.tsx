import View from "./View";
import React from "react";
import clone from "../util/clone";
import {useViewContext, ViewStateType} from "../view/ViewContext";

export default function Views () {

  const {viewState, setViewState} = useViewContext();

  function deleteView(index: number) {
    const newPeopleState = clone<ViewStateType>(viewState);
    newPeopleState.views.splice(index, 1);
    setViewState(newPeopleState);
  }

  return <>
    {viewState.views.map((p, i) => {
      return <View
        key={i}
        person={p.person}
        type={p.type}
        onDelete={() => deleteView(i)}
      />
    })}
  </>
}
