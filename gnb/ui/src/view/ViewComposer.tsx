import React, {ChangeEvent, useEffect, useState} from "react";
import {NEW_VIEW_MODAL_TITLE} from "../Placeholder";
import Modal from "../common/Modal";
import {PersonOption} from "../search/PersonOption";
import {PersonType} from "../elastic/model/PersonType";
import AddViewBtn from "./field/AddViewBtn";
import AddMentionedViewTypeahead from "./field/AddMentionedViewTypeahead";
import AddAttendantViewTypeahead from "./field/AddAttendantViewTypeahead";
import {ViewType, ViewTypes} from "./ViewTypes";
import SelectViewType from "./field/SelectViewType";
import {useViewContext} from "./ViewContext";

export default function ViewComposer() {

  const {viewState, setViewState} = useViewContext();

  const [state, setState] = useState<{ isOpen: boolean, viewType: ViewType | null }>({
    isOpen: false,
    viewType: null
  });

  useEffect(() => {
    setState(s => {
      return {...s, isOpen: false}
    })
  }, [viewState]);

  const handleSubmit = async (selected: PersonOption, type: PersonType) => {
    const newViews = viewState.views;
    newViews.push({person: selected.person, type});
    setViewState({...viewState, views: newViews});
  };

  function selectOption(e: ChangeEvent<HTMLSelectElement>) {
    setState({...state, viewType: ViewTypes.ATTENDANT});
  }

  return <div className="row mt-3">
    <Modal
      title={NEW_VIEW_MODAL_TITLE}
      isOpen={state.isOpen}
      handleClose={() => setState({...state, isOpen: false})}
    >
      <div className="form-group">

        <SelectViewType selected={state.viewType} selectOption={selectOption}/>

        {
          state.isOpen && state.viewType?.personType === PersonType.MENTIONED
            ? <AddMentionedViewTypeahead handleSubmit={handleSubmit}/> : null
        }
        {
          state.isOpen && state.viewType?.personType === PersonType.ATTENDANT
            ? <AddAttendantViewTypeahead handleSubmit={handleSubmit}/> : null
        }

      </div>
    </Modal>

    <div className="col">
      <div className="row-view bg-light">
        <AddViewBtn handleClick={() => setState({...state, isOpen: true})}/>
      </div>
    </div>
  </div>;
}
