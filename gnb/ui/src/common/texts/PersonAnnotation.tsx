import React from "react";
import {equal} from "../../util/equal";
import {Profile} from "./Profile";

type PersonAnnotationProps = {
  annotation: number
}

export const PersonAnnotation = React.memo(function (props: PersonAnnotationProps) {
  return <div className="card mb-3">
    <div className="card-body">
      <Profile person={props.annotation}/>
    </div>
  </div>;
}, (prev, next) => equal(prev.annotation, next.annotation));
