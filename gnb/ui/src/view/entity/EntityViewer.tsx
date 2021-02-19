import {D3Canvas} from "../../common/D3Canvas";
import {PersonHistogram} from "./PersonHistogram";
import React, {memo, useEffect, useRef, useState} from "react";
import {Person} from "../../elastic/model/Person";
import {equal} from "../../util/equal";
import {Texts} from "../../common/Texts";
import {Term} from "../model/Term";
import {isPerson, toPerson, ViewType} from "../model/ViewType";
import {TermHistogram} from "./TermHistogram";
import Place from "../model/Place";
import {PlaceHistogram} from "./PlaceHistogram";
import {highlightMentioned, highlightPlaces, toDom, toStr} from "../../util/highlight";

type EntityViewerProps = {
  entity: Person | Term | Place,
  type: ViewType
  memoKey: any
}

export const EntityViewer = memo(function (props: EntityViewerProps) {

  const svgRef = useRef(null);
  const [hasSvg, setHasSvg] = useState(svgRef.current);

  const [state, setState] = React.useState({
    ids: [] as string[],
    showTexts: false
  });

  useEffect(() => {
    setHasSvg(svgRef.current)
  }, [svgRef]);

  function renderPersonHistogram() {
    return <PersonHistogram
      handleResolutions={handleResolutions}
      svgRef={svgRef}
      person={props.entity as Person}
      type={toPerson(props.type)}
      memoKey={props.memoKey}
    />;
  }

  function renderTermHistogram() {
    return <TermHistogram
      handleResolutions={handleResolutions}
      svgRef={svgRef}
      term={props.entity as Term}
      memoKey={props.memoKey}
    />;
  }

  function renderPlaceHistogram() {
    return <PlaceHistogram
      handleResolutions={handleResolutions}
      svgRef={svgRef}
      place={props.entity as Place}
      memoKey={props.memoKey}
    />;

  }

  function handleResolutions(ids: string[]) {
    return setState({...state, ids, showTexts: true});
  }

  function highlightEntity(toHighlight: string) {
    const dom = toDom(toHighlight);
    if(props.type === ViewType.MENTIONED) {
      highlightMentioned(dom, [props.entity as Person])
    } else if (props.type === ViewType.PLACE) {
      highlightPlaces(dom, [props.entity as Place])
    }
    return toStr(dom);
  }

  return <>
    <D3Canvas svgRef={svgRef}/>

    {hasSvg && isPerson(props.type) ? renderPersonHistogram() : null}

    {hasSvg && props.type === ViewType.TERM ? renderTermHistogram() : null}

    {hasSvg && props.type === ViewType.PLACE ? renderPlaceHistogram() : null}

    {state.showTexts ? <Texts
      resolutions={state.ids}
      handleClose={() => setState({...state, showTexts: false})}
      highlightResolution={highlightEntity}
      highlightAttendants={props.type === ViewType.ATTENDANT ? [(props.entity as Person).id] : []}
      highlightFullText={props.type === ViewType.TERM ? (props.entity as Term).val : ''}
      memoKey={props.memoKey}
    /> : null}
  </>

}, ((prev, next) => equal(prev.memoKey, next.memoKey)));
