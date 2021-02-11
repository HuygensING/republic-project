import React, {memo, useState} from "react";
import Resolution from "../elastic/model/Resolution";
import Modal from "./Modal";
import {RESOLUTIONS_TEXTS_TITLE} from "../Placeholder";
import {useAsyncError} from "../hook/useAsyncError";
import {equal} from "../util/equal";
import {PersonType} from "../elastic/model/PersonType";
import {PersonAnn} from "../elastic/model/PersonAnn";
import {useSearchContext} from "../search/SearchContext";
import {joinJsx} from "../util/joinJsx";
import {Person} from "../elastic/model/Person";
import {useClientContext} from "../search/ClientContext";
import {usePrevious} from "../hook/usePrevious";

type TextsProps = {
  resolutions: string[],
  handleClose: () => void,
  memoKey: any
}

const domParser = new DOMParser();

export const Texts = memo(function (props: TextsProps) {

  const client = useClientContext().clientState.client;

  const [state, setResolutions] = useState({
    resolutions: [] as Resolution[],
    hasLoaded: false
  });

  const {searchState} = useSearchContext();

  const throwError = useAsyncError();

  if(!state.hasLoaded) {
    client.resolutionResource
      .getMulti(props.resolutions, searchState.fullText)
      .then((results) => {
        results = sortResolutions(results);
        setResolutions({resolutions: results, hasLoaded: true});
      })
      .catch(throwError);
  }

  const attendantIds = searchState.attendants.map(a => a.id);

  return (
    <Modal
      title={`${RESOLUTIONS_TEXTS_TITLE} (n=${state.resolutions.length})`}
      isOpen={true}
      handleClose={props.handleClose}
    >
      {state.hasLoaded ? state.resolutions.map((r: any, i: number) => {

        r.resolution.originalXml = highlightMentioned(r.resolution.originalXml, searchState.mentioned);

        return <div key={i}>
          <h5>{r.id}</h5>
          <small><strong>Aanwezigen</strong>: {r.people
            .filter((p: PersonAnn) => p.type === PersonType.ATTENDANT)
            .map((p: PersonAnn, i: number) => {
              const isAttendant = attendantIds.includes(p.id);
              return <span key={i} className={isAttendant ? 'highlight' : ''}>{p.name} (ID {p.id})</span>
            })
            .reduce(joinJsx)
          }</small>
          <div dangerouslySetInnerHTML={{__html: r.resolution.originalXml}}/>
        </div>;

      }) : 'Loading...'}
    </Modal>
  );

}, (prev, next) => equal(prev.memoKey, next.memoKey))


function sortResolutions(newResolutions: Resolution[]) {
  newResolutions = newResolutions.sort((a: any, b: any) => {
    const getResolutionIndex = (id: any) => parseInt(id.split('-').pop());
    return getResolutionIndex(a.id) - getResolutionIndex(b.id);
  });
  return newResolutions;
}

function highlightMentioned(originalXml: string, mentioned: Person[]) {
  if (mentioned.length === 0) {
    return originalXml;
  }
  const dom = domParser.parseFromString(originalXml, 'text/xml');
  for (const m of mentioned) {
    const found = dom.querySelectorAll(`[idnr="${m.id}"]`)?.item(0);
    if (found) {
      found.setAttribute('class', 'highlight');
    }
  }
  return dom.documentElement.outerHTML;
}
