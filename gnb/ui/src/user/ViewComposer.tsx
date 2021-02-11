import React from "react";
import {ADD_NEW_VIEW_BTN} from "../Placeholder";

export default function ViewComposer() {
  return <div className="row mt-3">
    <div className="col">
      <div className="row-view bg-light">
        <div className="d-flex align-items-center justify-content-center h-100">
          <div className="d-flex flex-column">
            <button type="button" className="btn btn-success align-self-center">{ADD_NEW_VIEW_BTN}</button>
          </div>
        </div>
      </div>
    </div>
  </div>
}
