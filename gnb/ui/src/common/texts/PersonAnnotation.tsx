import React from "react";
import {equal} from "../../util/equal";
import {Profile} from "./Profile";

type PersonAnnotationProps = {
  annotation: number,
  id: string
}

export const PersonAnnotation = React.memo(function (props: PersonAnnotationProps) {
  return <div className="card mb-3" id={props.id}>
    <div className="card-body">
      <Profile person={props.annotation}/>
    </div>
  </div>;
}, (prev, next) => equal(prev.annotation, next.annotation));
