import React, {useRef} from "react";
import DeleteViewButton from "./field/DeleteViewButton";
import useHover from "../hook/useHover";
import {useResolutionContext} from "../resolution/ResolutionContext";
import {EntityViewer} from "./entity/EntityViewer";
import {ViewType} from "./model/ViewType";
import {toStr, ViewEntityType} from "./model/ViewEntityType";
import {usePlotContext} from "../common/plot/PlotContext";

type ViewProps = {
  entity: ViewEntityType,
  type: ViewType
  onDelete: () => void;
}

export default function View(props: ViewProps) {

  const deleteRef = useRef(null)
  const isHovering = useHover(deleteRef);
  const {resolutionState} = useResolutionContext();
  const {plotState} = usePlotContext();

  function memoBy() {
    const resolutions = resolutionState.resolutions.map(r => r.ids).join(',');
    const strEntity = toStr(props.entity);
    return JSON.stringify([resolutions, props.type, strEntity, plotState.type]);
  }

  return <div className="row mt-3">
    <div className="col">

      <DeleteViewButton
        hoverRef={deleteRef}
        onClose={props.onDelete}
      />

      <div className={`row-view border border-white ${isHovering ? 'bg-light' : ''}`}>

        <EntityViewer
          entity={props.entity}
          type={props.type}
          memoKey={memoBy()}
        />

      </div>
    </div>
  </div>

}
