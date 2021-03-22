import React, {useEffect, useState} from "react";
import {Person} from "../../elastic/model/Person";
import {useClientContext} from "../../elastic/ClientContext";
import {equal} from "../../util/equal";

type ProfileProps = {
  person: number
}

type ProfileState = {
  person: Person
}

export const Profile = React.memo(function(props: ProfileProps){
  const client = useClientContext().clientState.client;
  const p2 = props.person;
  const [state, setState] = useState({} as ProfileState);

  useEffect(() => {
    client.peopleResource.getMulti([p2]).then((d) => {
      setState(s => {return {...s, person: d[0]}});
    });
  }, [p2, client.peopleResource]);

  if(!state.person) {
    return null;
  }

  const person = state.person;
  return <>
    <h5>{person.searchName}</h5>
    <p className="mb-1">
      <span>Aanwezig: <span className="badge badge-pill badge-info">{person.attendantCount}x</span> </span>
      <span>Genoemd: <span className="badge badge-pill badge-info">{person.mentionedCount}x</span> </span>
      <span>ID: <span className="badge badge-pill badge-info">{person.id}</span> </span>
    </p>
    {person.functions.length
      ? <>
        <p className="mb-0">Functies:</p>
        <ul className="mb-0">{person.functions.map(
          (func, i)  => <li className="small" key={i}>
            {func.name}
            <br/>
            <span className="text-muted">{func.start} t/m {func.end}</span>
          </li>
        )}</ul>
      </>
      : null}
  </>

}, (prev, next) => equal(prev.person, next.person));
