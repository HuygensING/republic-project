import {D3Canvas} from "../../common/plot/D3Canvas";
import {PersonPlot} from "./PersonPlot";
import React, {useRef} from "react";
import {Person} from "../../elastic/model/Person";
import {Texts} from "../../common/texts/Texts";
import {Term} from "../model/Term";
import {isPerson, toPerson, ViewType} from "../model/ViewType";
import {TermPlot} from "./TermPlot";
import Place from "../model/Place";
import {PlacePlot} from "./PlacePlot";
import {highlightMentioned, highlightPlaces, toDom, toStr} from "../../util/highlight";
import {ViewEntityType} from "../model/ViewEntityType";
import {PersonFunction} from "../../elastic/model/PersonFunction";
import {FunctionPlot} from "./FunctionPlot";
import {FunctionCategoryPlot} from "./FunctionCategoryPlot";
import {PersonFunctionCategory} from "../../elastic/model/PersonFunctionCategory";

type EntityViewerProps = {
  entity: ViewEntityType,
  type: ViewType
  memoKey: any
}

export const EntityViewer = function (props: EntityViewerProps) {

  const svgRef = useRef(null);

  const [state, setState] = React.useState({
    ids: [] as string[],
    showTexts: false
  });

  function renderPersonHistogram() {
    return <PersonPlot
      handleResolutions={handleResolutions}
      svgRef={svgRef}
      person={props.entity as Person}
      type={toPerson(props.type)}
      memoKey={props.memoKey}
    />;
  }

  function renderTermHistogram() {
    return <TermPlot
      handleResolutions={handleResolutions}
      svgRef={svgRef}
      term={props.entity as Term}
      memoKey={props.memoKey}
    />;
  }

  function renderPlaceHistogram() {
    return <PlacePlot
      handleResolutions={handleResolutions}
      svgRef={svgRef}
      place={props.entity as Place}
      memoKey={props.memoKey}
    />;
  }

  function renderFunctionHistogram() {
    return <FunctionPlot
      handleResolutions={handleResolutions}
      svgRef={svgRef}
      personFunction={props.entity as PersonFunction}
      memoKey={props.memoKey}
    />;
  }

  function renderFunctionCategoryHistogram() {
    return <FunctionCategoryPlot
      handleResolutions={handleResolutions}
      svgRef={svgRef}
      personFunctionCategory={props.entity as PersonFunctionCategory}
      memoKey={props.memoKey}
    />;
  }

  function handleResolutions(ids: string[]) {
    return setState({...state, ids, showTexts: true});
  }

  function highlightEntity(originalXml: string) {
    const dom = toDom(originalXml);
    if (props.type === ViewType.MENTIONED) {
      highlightMentioned(dom, [(props.entity as Person).id])
    } else if (props.type === ViewType.FUNCTION) {
      highlightMentioned(dom, (props.entity as PersonFunction).people)
    } else if (props.type === ViewType.FUNCTION_CATEGORY) {
      highlightMentioned(dom, (props.entity as PersonFunctionCategory).people)
    } else if (props.type === ViewType.PLACE) {
      highlightPlaces(dom, [props.entity as Place]);
    }
    return toStr(dom);
  }

  function getAttendants(props: EntityViewerProps): number[] {
    if (props.type === ViewType.ATTENDANT) {
      return [(props.entity as Person).id];
    }
    return [];
  }

  return <>
    <D3Canvas svgRef={svgRef}/>

    {isPerson(props.type) ? renderPersonHistogram() : null}
    {props.type === ViewType.TERM ? renderTermHistogram() : null}
    {props.type === ViewType.PLACE ? renderPlaceHistogram() : null}
    {props.type === ViewType.FUNCTION ? renderFunctionHistogram() : null}
    {props.type === ViewType.FUNCTION_CATEGORY ? renderFunctionCategoryHistogram() : null}

    {state.showTexts ? <Texts
      resolutions={state.ids}
      handleClose={() => setState({...state, showTexts: false})}
      highlightAttendants={getAttendants(props)}
      highlightQuery={props.type === ViewType.TERM ? (props.entity as Term).val : ''}
      highlightXml={highlightEntity}
      memoKey={props.memoKey}
    /> : null}
  </>

};
