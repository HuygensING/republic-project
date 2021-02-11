import {PeopleStateType, usePeopleContext} from "./person/PeopleContext";
import UserView from "./user/UserView";
import React from "react";

export default function UserViews () {

  const {peopleState, setPeopleState} = usePeopleContext();

  function deleteView(index: number) {
    const newPeopleState = JSON.parse(JSON.stringify(peopleState)) as PeopleStateType;
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
