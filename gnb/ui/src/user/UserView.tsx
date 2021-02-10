import React, {useRef} from "react";
import GnbElasticClient from "../elastic/GnbElasticClient";
import {Person} from "../elastic/model/Person";
import {PersonType} from "../elastic/model/PersonType";
import DeleteButton from "./DeleteButton";
import useHover from "../hook/useHover";
import PersonViewer from "../person/PersonViewer";

type UserViewerProps = {
  client: GnbElasticClient,
  person: Person,
  type: PersonType
  onDelete: () => void;
}

export default function UserView(props: UserViewerProps) {

  const deleteRef = useRef(null)
  const isHovering = useHover(deleteRef);

  return <div className="row mt-3">
    <div className="col">
      <div className={`border border-white ${isHovering ? 'bg-light' : ''}`}>

        <DeleteButton
          hoverRef={deleteRef}
          onClose={props.onDelete}
        />

        <PersonViewer person={props.person} client={props.client} type={props.type} />

      </div>
    </div>
  </div>;

}
