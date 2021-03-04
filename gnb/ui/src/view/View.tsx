import React, {useRef} from "react";
import DeleteViewButton from "./field/DeleteViewButton";
import useHover from "../hook/useHover";
import {useResolutionContext} from "../resolution/ResolutionContext";
import {EntityViewer} from "./entity/EntityViewer";
import {ViewType} from "./model/ViewType";
import {ViewEntityType, toString} from "./model/ViewEntityType";

type ViewProps = {
  entity: ViewEntityType,
  type: ViewType
  onDelete: () => void;
}

export default function View(props: ViewProps) {

  const deleteRef = useRef(null)
  const isHovering = useHover(deleteRef);
  const {resolutionState} = useResolutionContext();

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
          memoKey={[resolutionState.updatedOn, props.type, toString(props.entity)]}
        />

      </div>
    </div>
  </div>

}
