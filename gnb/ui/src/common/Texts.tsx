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
import {useClientContext} from "../elastic/ClientContext";
import {highlightMentioned, highlightPlaces, toDom, toStr} from "../util/highlight";
import Place from "../view/model/Place";

type TextsProps = {
  resolutions: string[],
  handleClose: () => void,

  /**
   * Ids of attendants to highlight
   */
  highlightAttendants?: number[]

  /**
   * Query_string query to highlight originalXml using elasticsearch highlighting
   */
  highlightQuery?: string

  /**
   * Function to highlight resolution.originalXml
   * To highlight something: add the class name 'highlight'
   */
  highlightXml?: (originalXml: string) => string

  memoKey: any
}

export const Texts = memo(function (props: TextsProps) {

  const client = useClientContext().clientState.client;

  const [state, setResolutions] = useState({
    resolutions: [] as Resolution[],
    hasLoaded: false
  });

  const {searchState} = useSearchContext();

  const throwError = useAsyncError();

  if(!state.hasLoaded) {
    let fullTextHighlight = searchState.fullText;
    if(props.highlightQuery) {
      fullTextHighlight += ' ' + props.highlightQuery;
    }
    client.resolutionResource
      .getMulti(props.resolutions, fullTextHighlight)
      .then((results) => {
        results = sortResolutions(results);
        setResolutions({resolutions: results, hasLoaded: true});
      })
      .catch(throwError);
  }

  const peopleWithFunction = Array.from(new Set(([] as number[]).concat(
    ...searchState.functions.map(f => f.people))
  ));

  const mentionedToHighlight : number[] = [...searchState.mentioned.map(m => m.id), ...peopleWithFunction];
  const attendantsToHighlight : number[] = [...searchState.attendants.map(a => a.id), ...peopleWithFunction];

  if(props.highlightAttendants) {
    attendantsToHighlight.push(...props.highlightAttendants);
  }

  return (
    <Modal
      title={`${RESOLUTIONS_TEXTS_TITLE} (n=${state.resolutions.length})`}
      isOpen={true}
      handleClose={props.handleClose}
    >
      {state.hasLoaded ? state.resolutions.map((r: any, i: number) => {
        let highlighted = highlight(
          r.resolution.originalXml,
          mentionedToHighlight,
          searchState.places,
        );

        if(props.highlightXml) {
          highlighted = props.highlightXml(highlighted);
        }

        return <div key={i}>
          <h5>{r.id}</h5>
          <small><strong>Aanwezigen</strong>: {renderAttendants(r, attendantsToHighlight)}</small>
          <div dangerouslySetInnerHTML={{__html: highlighted}}/>
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

function renderAttendants(r: any, markedIds: number[]) {
  if(!r.people.length) {
    return '-';
  }
  return r.people
    .filter((p: PersonAnn) => p.type === PersonType.ATTENDANT)
    .map((p: PersonAnn, i: number) => {
      const isAttendant = markedIds.includes(p.id);
      return <span key={i} className={isAttendant ? 'highlight' : ''}>{p.name} (ID {p.id})</span>
    })
    .reduce(joinJsx);
}


function highlight(
  xml: string,
  mentioned: number[],
  places: Place[],
) : string {
  const dom = toDom(xml);

  highlightMentioned(dom, mentioned);
  highlightPlaces(dom, places);

  return toStr(dom);
}
