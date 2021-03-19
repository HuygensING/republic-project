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
  console.log('props', props.person);
  const client = useClientContext().clientState.client;
  const p2 = props.person;
  const [state, setState] = useState({} as ProfileState);

  useEffect(() => {
    client.peopleResource.getMulti([p2]).then((d) => {
      setState(s => {return {...s, person: d[0]}});
    });
  }, [p2, client.peopleResource]);

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
    {p.functions.length
      ? <>
        <p className="mb-0">Functies:</p>
        <ul className="mb-0">{p.functions.map(
          (f, i)  => <li className="small" key={i}>
            {f.name}
            <br/>
            <span className="text-muted">{f.start} t/m {f.end}</span>
          </li>
        )}</ul>
      </>
      : null}
  </>

}, (p, n) => equal(p.person, n.person));
