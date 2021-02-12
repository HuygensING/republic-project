import React, {useRef} from "react";
import {Person} from "../elastic/model/Person";
import {PersonType} from "../elastic/model/PersonType";
import DeleteViewButton from "./DeleteViewButton";
import useHover from "../hook/useHover";
import {useResolutionContext} from "../resolution/ResolutionContext";
import {PersonViewer} from "../view/PersonViewer";

type UserViewerProps = {
  person: Person,
  type: PersonType
  onDelete: () => void;
}

export default function View(props: UserViewerProps) {

  const deleteRef = useRef(null)
  const isHovering = useHover(deleteRef);
  const {resolutionState} = useResolutionContext();

  return <div className="row mt-3">
    <div className="col">
      <div className={`row-view border border-white ${isHovering ? 'bg-light' : ''}`}>

        <PersonViewer
          person={props.person}
          type={props.type}
          memoKey={[resolutionState.updatedOn, props.type, props.person.id]}
        />

        <DeleteViewButton
          hoverRef={deleteRef}
          onClose={props.onDelete}
        />

      </div>
    </div>
  </div>

}
