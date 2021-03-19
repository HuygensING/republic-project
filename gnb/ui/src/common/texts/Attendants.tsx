import React, {useState} from "react";
import Resolution from "../../elastic/model/Resolution";
import {PersonAnn} from "../../elastic/model/PersonAnn";
import {joinJsx} from "../../util/joinJsx";
import {useClientContext} from "../../elastic/ClientContext";
import {Person} from "../../elastic/model/Person";
import Attendant from "./Attendant";

type AttendantProps = {
  resolution: Resolution,
  markedIds: number[]
}

type StateType = {
  show: boolean,
  person?: number
}

export function Attendants(props: AttendantProps) {
  const r = props.resolution;

  const [state, setState] = useState({
    show: false,
  } as StateType);

  async function toggle(i: number) {
    const personAnn = r.people[i];
    setState({...state, person: personAnn.id, show: !state.show});
  }

  const p = state.person;

  return <>
    <div className="accordion mb-2">
      <div className="card">
        <div className="card-header attendants-card">

          <small><strong>Aanwezigen:</strong> {r.people.sort(presidentFirst).map(
            (a: PersonAnn, i: number) =>
              <a className={highlightMarked(a)} onClick={() => toggle(i)} key={i}>
                {a.name}{a.president ? ' (president)' : ''}
              </a>
          ).reduce(joinJsx)}
          </small>
        </div>
        {p ?
          <div className={`collapse ${state.show ? 'show' : 'hide'}`}>
            <div className="card-body">
              <Attendant person={p} />
            </div>
          </div>
          : null}
      </div>
    </div>
  </>;

  function presidentFirst(a: PersonAnn, b: PersonAnn) {
    return a.president ? -1 : b.president ? 1 : 0;
  }

  function isMarked(p: any) {
    return props.markedIds.includes(p.id);
  }

  function highlightMarked(a: any) {
    return isMarked(a) ? 'highlight' : '';
  }

}
