import React, {useEffect, useState} from "react";
import {ADD_NEW_VIEW_BTN, NEW_VIEW_MODAL_TITLE, PLOT_ATTENDANT} from "../Placeholder";
import {usePeopleContext} from "../person/PeopleContext";
import Modal from "../common/Modal";
import {PersonOption} from "../search/PersonOption";
import PeopleTypeahead from "../search/field/PeopleTypeahead";
import {PersonType} from "../elastic/model/PersonType";

export default function ViewComposer() {

  const {peopleState, setPeopleState} = usePeopleContext();

  const [state, setState] = useState({
    isOpen: false
  });

  useEffect(() => {
    setState(s => {
      return {...s, isOpen: false}
    })
  }, [peopleState]);

  const handleSubmit = async (selected: PersonOption[]) => {
    const newPeople = peopleState.people;
    newPeople.push({person: selected[0].person, type: PersonType.ATTENDANT});
    setPeopleState({...peopleState, people: newPeople});
  };

  return <div className="row mt-3">
    <Modal
      title={NEW_VIEW_MODAL_TITLE}
      isOpen={state.isOpen}
      handleClose={() => setState({...state, isOpen: false})}
    >
      <div className="form-group">
        {
          state.isOpen
            ? <PeopleTypeahead
              placeholder={PLOT_ATTENDANT}
              personType={PersonType.ATTENDANT}
              handleSubmit={handleSubmit}
              id="attendants-typeahead"
            />
            : null
        }
      </div>
    </Modal>

    <div className="col">
      <div className="row-view bg-light">
        <div className="d-flex align-items-center justify-content-center h-100">
          <div className="d-flex flex-column">
            <button
              onClick={() => setState({...state, isOpen: true})}
              type="button"
              className="btn btn-success align-self-center"
            >
              {ADD_NEW_VIEW_BTN}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
}
