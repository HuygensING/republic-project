import React from "react";
import {ADD_NEW_VIEW_BTN} from "../Placeholder";
import {defaultPeopleContext, PersonWithType, usePeopleContext} from "../person/PeopleContext";
import {Person} from "../elastic/model/Person";
import clone from "../util/clone";

export default function ViewComposer() {

  const {peopleState, setPeopleState} = usePeopleContext();

  function addView() {
    const newPeople = peopleState.people;
    newPeople.push(clone<PersonWithType>(defaultPeopleContext.peopleState.people[0]));
    setPeopleState({people: newPeople});
  }

  return <div className="row mt-3">
    <div className="col">
      <div className="row-view bg-light">
        <div className="d-flex align-items-center justify-content-center h-100">
          <div className="d-flex flex-column">
            <button
              onClick={addView}
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
