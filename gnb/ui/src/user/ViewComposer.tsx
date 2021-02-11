import React, {ChangeEvent, useEffect, useState} from "react";
import {
  ADD_NEW_VIEW_BTN,
  ATTENDANT,
  MENTIONED,
  NEW_VIEW_MODAL_TITLE,
  PICK_USER_VIEW,
  PLOT_ATTENDANT,
  PLOT_MENTIONED,
  SEARCH_TERM
} from "../Placeholder";
import {usePeopleContext} from "../person/PeopleContext";
import Modal from "../common/Modal";
import {PersonOption} from "../search/PersonOption";
import PeopleTypeahead from "../search/field/PeopleTypeahead";
import {PersonType} from "../elastic/model/PersonType";

export type PlotType = {
  type: string,
  personType?: PersonType,
  placeholder: string
};

const plotTypes: PlotType[] = [
  {
    type: 'attendant',
    personType: PersonType.ATTENDANT,
    placeholder: ATTENDANT
  },
  {
    type: 'mentioned',
    personType: PersonType.MENTIONED,
    placeholder: MENTIONED
  },
  {
    type: 'term',
    placeholder: SEARCH_TERM
  }
];

export default function ViewComposer() {

  const {peopleState, setPeopleState} = usePeopleContext();

  const [state, setState] = useState({
    isOpen: false,
    plotType: plotTypes[0]
  });

  useEffect(() => {
    setState(s => {
      return {...s, isOpen: false}
    })
  }, [peopleState]);

  const handleSubmit = async (selected: PersonOption[], type: PersonType) => {
    const newPeople = peopleState.people;
    newPeople.push({person: selected[0].person, type});
    setPeopleState({...peopleState, people: newPeople});
  };

  function selectOption(e: ChangeEvent<HTMLSelectElement>) {
    setState({...state, plotType: plotTypes.find(t => t.type === e.target.value) || plotTypes[0]});
  }

  function createOptions() {
    return plotTypes.map((type, index) => {
      return <option
        key={index}
        value={type.type}
      >
        {type.placeholder}
      </option>
    });
  }

  return <div className="row mt-3">
    <Modal
      title={NEW_VIEW_MODAL_TITLE}
      isOpen={state.isOpen}
      handleClose={() => setState({...state, isOpen: false})}
    >
      <div className="form-group">

        <div className="form-group">
          <label htmlFor="formControlSelect">{PICK_USER_VIEW}</label>
          <select
            className="form-control"
            id="formControlSelect"
            onChange={selectOption}
            value={state.plotType.type}
          >
            {createOptions()}
          </select>
        </div>

        {
          state.isOpen && state.plotType.personType === PersonType.ATTENDANT
            ? <PeopleTypeahead
              placeholder={PLOT_ATTENDANT}
              personType={PersonType.ATTENDANT}
              handleSubmit={(o) => handleSubmit(o, PersonType.ATTENDANT)}
              id="attendants-typeahead"
            />
            : null
        }

        {
          state.isOpen && state.plotType.personType === PersonType.MENTIONED
            ? <PeopleTypeahead
              placeholder={PLOT_MENTIONED}
              personType={PersonType.MENTIONED}
              handleSubmit={(o) => handleSubmit(o, PersonType.MENTIONED)}
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
