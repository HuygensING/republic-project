import React, {useRef} from "react";
import {Person} from "../elastic/model/Person";
import {PersonType} from "../elastic/model/PersonType";
import DeleteButton from "./DeleteButton";
import useHover from "../hook/useHover";
import {PersonViewer} from "../person/PersonViewer";
import {useResolutionContext} from "../resolution/ResolutionContext";

type UserViewerProps = {
  person: Person,
  type: PersonType
  onDelete: () => void;
}

export default function UserView(props: UserViewerProps) {

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

        <DeleteButton
          hoverRef={deleteRef}
          onClose={props.onDelete}
        />

      </div>
    </div>
  </div>

}
