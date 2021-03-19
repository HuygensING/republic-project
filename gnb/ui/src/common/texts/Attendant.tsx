import React, {useEffect, useState} from "react";
import {Person} from "../../elastic/model/Person";
import {useClientContext} from "../../elastic/ClientContext";

type AttendantProps = {
  person: number
}

type AttendantState = {
  person: Person
}

export default function Attendant (props: AttendantProps){
  const client = useClientContext().clientState.client;

  const [state, setState] = useState({} as AttendantState);

  useEffect(() => {
    client.peopleResource.getMulti([props.person]).then((d) => {
      setState({...state, person: d[0]});
    });
  });

  if(!state.person) {
    return <></>
  }

  const p = state.person;
  return <>
    <h5>{p.searchName}</h5>
    <p className="mb-1">
      <span>Aanwezig: <span className="badge badge-pill badge-info">{p.attendantCount}x</span> </span>
      <span>Genoemd: <span className="badge badge-pill badge-info">{p.mentionedCount}x</span> </span>
      <span>ID: <span className="badge badge-pill badge-info">{p.id}</span> </span>
    </p>
    {p.functions
      ? <>
        <p className="mb-0">Functies:</p>
        <ul className="mb-0">{p.functions.map(
          f => <li className="small">
            {f.name}
            <br/>
            <span className="text-muted">{f.start} t/m {f.end}</span>
          </li>
        )}</ul>
      </>
      : null}
  </>

}
