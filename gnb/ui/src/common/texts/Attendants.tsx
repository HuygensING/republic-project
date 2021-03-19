import React, {useState} from "react";
import Resolution from "../../elastic/model/Resolution";
import {PersonAnn} from "../../elastic/model/PersonAnn";
import {joinJsx} from "../../util/joinJsx";
import {useClientContext} from "../../elastic/ClientContext";
import {Person} from "../../elastic/model/Person";

type AttendantProps = {
  resolution: Resolution,
  markedIds: number[]
}

type StateType = {
  show: boolean,
  person?: Person
}

export function Attendants(props: AttendantProps) {
  const r = props.resolution;

  const client = useClientContext().clientState.client;

  const [state, setState] = useState({
    show: false,
  } as StateType);

  async function toggle(i: number) {
    const personAnn = r.people[i];
    const person = (await client.peopleResource.getMulti([personAnn.id]))[0];
    setState({...state, person, show: !state.show});
  }

  function isMarked(p: any) {
    return props.markedIds.includes(p.id);
  }

  const p = state.person;

  function highlightMarked(a: any) {
    return isMarked(a) ? 'highlight' : '';
  }

  return <>
    <div className="accordion mb-2">
      <div className="card">
        <div className="card-header attendants-card">

          <small><strong>Aanwezigen:</strong> {r.people.sort(presidentFirst).map(
            (a: PersonAnn, i: number) =>
              <a className={highlightMarked(a)} onClick={() => toggle(i)} key={i}>
                {a.name} {a.president ? '(president)' : ''}
              </a>
          ).reduce(joinJsx)}
          </small>
        </div>
        {p ?
          <div className={`collapse ${state.show ? 'show' : 'hide'}`}>
            <div className="card-body">
              <h5>{p.searchName}</h5>
              <p className="mb-1">
                <span>Aanwezig: <span className="badge badge-pill badge-info">{p.mentionedCount}x</span> </span>
                <span>Genoemd: <span className="badge badge-pill badge-info">{p.attendantCount}x</span> </span>
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
            </div>
          </div>
          : null}
      </div>
    </div>
  </>;

  function presidentFirst(a: PersonAnn, b: PersonAnn) {
    return a.president ? -1 : b.president ? 1 : 0;
  }

}
