import View from "./View";
import React from "react";
import clone from "../util/clone";
import {useViewContext, ViewStateType} from "./ViewContext";

/**
 * Contains custom plots created by the ViewComposer
 */
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
          key={v.key}
          entity={v.entity}
          type={v.type}
          onDelete={() => deleteView(i)}
        />

    })}
  </>
}
