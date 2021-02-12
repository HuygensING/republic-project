import React, {useRef} from "react";
import {Person} from "../elastic/model/Person";
import DeleteViewButton from "./field/DeleteViewButton";
import useHover from "../hook/useHover";
import {useResolutionContext} from "../resolution/ResolutionContext";
import {EntityViewer} from "./entity/EntityViewer";
import {toString, ViewType} from "./ViewTypes";
import {Term} from "./Term";

type ViewProps = {
  entity: Person | Term,
  type: ViewType
  onDelete: () => void;
}

export default function View(props: ViewProps) {

  const deleteRef = useRef(null)
  const isHovering = useHover(deleteRef);
  const {resolutionState} = useResolutionContext();

  return <div className="row mt-3">
    <div className="col">
      <div className={`row-view border border-white ${isHovering ? 'bg-light' : ''}`}>

        <EntityViewer
          entity={props.entity}
          type={props.type}
          memoKey={[resolutionState.updatedOn, props.type, toString(props.entity)]}
        />

        <DeleteViewButton
          hoverRef={deleteRef}
          onClose={props.onDelete}
        />

      </div>
    </div>
  </div>

}
