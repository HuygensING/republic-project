import View from "./View";
import React from "react";
import clone from "../util/clone";
import {useViewContext, ViewStateType} from "./ViewContext";

export default function Views () {

  const {viewState, setViewState} = useViewContext();

  function deleteView(index: number) {
    const newPeopleState = clone<ViewStateType>(viewState);
    newPeopleState.views.splice(index, 1);
    setViewState(newPeopleState);
  }

  return <>
    {viewState.views.map((v, i) => {
        return <View
          key={i}
          entity={v.entity}
          type={v.type}
          onDelete={() => deleteView(i)}
        />

    })}
  </>
}
