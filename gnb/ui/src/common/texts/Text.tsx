import {RESOLUTION} from "../../content/Placeholder";
import {Attendants} from "./Attendants";
import React, {useEffect, useState} from "react";
import Place from "../../view/model/Place";
import {highlightMentioned, highlightPlaces, toDom, toStr} from "../../util/highlight";
import {useSearchContext} from "../../search/SearchContext";
import Resolution from "../../elastic/model/Resolution";
import {PersonAnnotation} from "./PersonAnnotation";

import smoothscroll from 'smoothscroll-polyfill';

smoothscroll.polyfill();

type TextProps = {
  resolution: Resolution,
  attendantsToHighlight: number[],
  mentionedToHighlight: number[],
  highlightXml?: (originalXml: string) => string
}

type TextState = {
  annotation?: number
}

export function Text(props: TextProps) {
  const {searchState} = useSearchContext();

  const [state, setState] = useState({
    hasLoaded: false
  } as TextState);

  const r = props.resolution;

  let highlighted = highlight(
    r.resolution.originalXml,
    props.mentionedToHighlight,
    searchState.places,
  );

  if (props.highlightXml) {
    highlighted = props.highlightXml(highlighted);
  }

  const ann = state.annotation;
  const annId = r.id + '_' + ann;

  useEffect(() => {
    const anchor = document.getElementById(annId);
    anchor?.scrollIntoView({behavior: 'smooth'});
  }, [annId])

  function handlePersonClick(e: React.MouseEvent<HTMLElement>) {
    const nodeName = (e.target as any).nodeName;
    if (nodeName !== 'PERSOON') {
      return;
    }
    setState(s => {
      return {...s, annotation: parseInt((e.target as any).getAttribute('idnr'))}
    });
  }

  return <div>
    <h5>{RESOLUTION} {r.metadata.meeting.date} #{r.metadata.resolution}</h5>
    <Attendants resolution={r} markedIds={props.attendantsToHighlight}/>
    <div
      dangerouslySetInnerHTML={{__html: highlighted}}
      onClick={handlePersonClick}
    />
    {ann ? <PersonAnnotation annotation={ann} id={annId}/> : null}
  </div>;

}

function highlight(
  xml: string,
  mentioned: number[],
  places: Place[],
): string {
  const dom = toDom(xml);

  highlightMentioned(dom, mentioned);
  highlightPlaces(dom, places);

  return toStr(dom);
}

