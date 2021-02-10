import {PeopleStateType, usePeopleContext} from "./person/PeopleContext";
import UserView from "./user/UserView";
import React from "react";
import GnbElasticClient from "./elastic/GnbElasticClient";

type UserViewersProps = {
  client: GnbElasticClient;
}

export default function UserViews (props: UserViewersProps) {

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
        client={props.client}
        person={p.person}
        type={p.type}
        onDelete={() => deleteView(i)}
      />
    })}
  </>;
}
