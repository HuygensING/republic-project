import React, {ChangeEvent, useEffect, useState} from "react";
import {NEW_VIEW_MODAL_TITLE} from "../Placeholder";
import Modal from "../common/Modal";
import AddViewBtn from "./field/AddViewBtn";
import AddMentionedViewTypeahead from "./field/AddMentionedViewTypeahead";
import AddAttendantViewTypeahead from "./field/AddAttendantViewTypeahead";
import {fromValue, ViewType} from "./model/ViewType";
import SelectViewType from "./field/SelectViewType";
import {useViewContext} from "./ViewContext";
import AddTermFormField from "./field/AddTermFormField";
import {Term} from "./model/Term";
import {Person} from "../elastic/model/Person";
import LocationTypeahead from "./field/LocationTypeahead";
import Location from "./model/Location";
export default function ViewComposer() {

  // TODO: add location as ViewType, option and 'AddLocationFormField'

  const {viewState, setViewState} = useViewContext();

  const [state, setState] = useState<{ isOpen: boolean, viewType: ViewType | undefined }>({
    isOpen: false,
    viewType: undefined
  });

  useEffect(() => {
    setState(s => {
      return {...s, isOpen: false}
    })
  }, [viewState]);

  function selectOption(e: ChangeEvent<HTMLSelectElement>) {
    setState({...state, viewType: fromValue(e.target.value)});
  }

  const handleSubmit = async (selected: Person | Term | Location, type: ViewType) => {
    const newViews = viewState.views;
    newViews.push({entity: selected, type});
    setViewState({...viewState, views: newViews});
  };

  return <div className="row mt-3">
    <Modal
      title={NEW_VIEW_MODAL_TITLE}
      isOpen={state.isOpen}
      handleClose={() => setState({...state, isOpen: false})}
    >
      <div className="form-group">

        <SelectViewType selected={state.viewType} selectOption={selectOption}/>

        {
          state.isOpen && state.viewType === ViewType.MENTIONED
            ? <AddMentionedViewTypeahead handleSubmit={handleSubmit}/> : null
        }
        {
          state.isOpen && state.viewType === ViewType.ATTENDANT
            ? <AddAttendantViewTypeahead handleSubmit={handleSubmit}/> : null
        }
        {
          state.isOpen && state.viewType === ViewType.TERM
            ? <AddTermFormField handleSubmit={handleSubmit}/> : null
        }
        {
          state.isOpen && state.viewType === ViewType.LOCATION
            ? <LocationTypeahead handleSubmit={handleSubmit}/> : null
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
