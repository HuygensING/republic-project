import {D3Canvas} from "../../common/D3Canvas";
import {PersonHistogram} from "./PersonHistogram";
import React, {memo, useEffect, useRef, useState} from "react";
import {Person} from "../../elastic/model/Person";
import {equal} from "../../util/equal";
import {Texts} from "../../common/Texts";
import {Term} from "../Term";
import {isPerson, toPerson, ViewType} from "../ViewTypes";
import {TermHistogram} from "./TermHistogram";

type EntityViewerProps = {
  entity: Person | Term,
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
      handleResolutions={(ids: string[]) => setState({...state, ids, showTexts: true})}
      svgRef={svgRef}
      person={props.entity as Person}
      type={toPerson(props.type)}
      memoKey={props.memoKey}
    />;
  }

  function renderTermHistogram() {
    return <TermHistogram
      handleResolutions={(ids: string[]) => setState({...state, ids, showTexts: true})}
      svgRef={svgRef}
      term={props.entity as Term}
      memoKey={props.memoKey}
    />;
  }

  return <>
    <D3Canvas svgRef={svgRef}/>

    {hasSvg && isPerson(props.type) ? renderPersonHistogram() : null}

    {hasSvg && props.type === ViewType.TERM ? renderTermHistogram() : null}

    {state.showTexts ? <Texts
      resolutions={state.ids}
      handleClose={() => setState({...state, showTexts: false})}
      memoKey={props.memoKey}
    /> : null}
  </>

}, ((prev, next) => equal(prev.memoKey, next.memoKey)));
