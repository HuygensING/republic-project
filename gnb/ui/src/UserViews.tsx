import {PeopleStateType, usePeopleContext} from "./person/PeopleContext";
import UserView from "./user/UserView";
import React from "react";
import clone from "./util/clone";

export default function UserViews () {

  const {peopleState, setPeopleState} = usePeopleContext();

  function deleteView(index: number) {
    const newPeopleState = clone<PeopleStateType>(peopleState);
    newPeopleState.people.splice(index, 1);
    setPeopleState(newPeopleState);
  }

  return <>
    {peopleState.people.map((p, i) => {
      return <UserView
        key={i}
        person={p.person}
        type={p.type}
        onDelete={() => deleteView(i)}
      />
    })}
  </>
}
