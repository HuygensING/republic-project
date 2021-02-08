import {PeopleStateType, usePeopleContext} from "./person/PeopleContext";
import PersonViewer from "./person/PersonViewer";
import React from "react";
import GnbElasticClient from "./elastic/GnbElasticClient";

type UserViewersProps = {
  client: GnbElasticClient;
}

export default function UserViewers (props: UserViewersProps) {

  const {peopleState, setPeopleState} = usePeopleContext();

  function deleteView(index: number) {
    const newPeopleState = JSON.parse(JSON.stringify(peopleState)) as PeopleStateType;
    newPeopleState.people.splice(index, 1);
    console.log('newPeopleState', newPeopleState);
    setPeopleState(newPeopleState);
  }

  return <>
    {peopleState.people.map((p, i) => {
      return <PersonViewer
        key={i}
        client={props.client}
        person={p.person}
        type={p.type}
        onDelete={() => deleteView(i)}
      />
    })}
  </>;
}
