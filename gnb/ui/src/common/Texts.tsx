import React, {memo, useState} from "react";
import Resolution from "../elastic/model/Resolution";
import Modal from "./Modal";
import {RESOLUTIONS_TEXTS_TITLE} from "../content/Placeholder";
import {useAsyncError} from "../hook/useAsyncError";
import {equal} from "../util/equal";
import {PersonType} from "../elastic/model/PersonType";
import {PersonAnn} from "../elastic/model/PersonAnn";
import {useSearchContext} from "../search/SearchContext";
import {joinJsx} from "../util/joinJsx";
import {Person} from "../elastic/model/Person";
import {useClientContext} from "../elastic/ClientContext";
import Place from "../view/model/Place";

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
        const highlightedXml = highlight(r.resolution.originalXml, searchState.mentioned, searchState.places);
        return <div key={i}>
          <h5>{r.id}</h5>
          <small><strong>Aanwezigen</strong>: {renderAttendants(r, attendantIds)}</small>
          <div dangerouslySetInnerHTML={{__html: highlightedXml}}/>
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

function highlight(originalXml: string, mentioned: Person[], places: Place[]) : string {
  console.log('highlight', mentioned, places);

  if (mentioned.length === 0 && places.length === 0) {
    return originalXml;
  }

  const dom = domParser.parseFromString(originalXml, 'text/xml');

  highlightMentioned(mentioned, dom);
  highlightPlaces(dom, places);

  return dom.documentElement.outerHTML;
}

function highlightMentioned(mentioned: Person[], dom: Document) {
  for (const m of mentioned) {
    const found = dom.querySelectorAll(`[idnr="${m.id}"]`)?.item(0);
    if (found) {
      found.setAttribute('class', 'highlight');
    }
  }
}

function highlightPlaces(dom: Document, places: Place[]) {
  const found = dom.getElementsByTagName('plaats');
  for (const p of places) {
    for (const f of found) {
      if (f.textContent?.toLowerCase() === p.val.toLowerCase()) {
        f.setAttribute('class', 'highlight');
      }
    }
  }
}

function renderAttendants(r: any, markedIds: number[]) {
  const rendered = r.people
    .filter((p: PersonAnn) => p.type === PersonType.ATTENDANT)
    .map((p: PersonAnn, i: number) => {
      const isAttendant = markedIds.includes(p.id);
      return <span key={i} className={isAttendant ? 'highlight' : ''}>{p.name} (ID {p.id})</span>
    })
    .reduce(joinJsx, []);
  return rendered.length ? rendered : '-';
}

