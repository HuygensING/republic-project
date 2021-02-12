import {ADD_NEW_VIEW_BTN} from "../Placeholder";
import React from "react";

type AddViewBtnProps = {
  handleClick: () => void
}

export default function AddViewBtn(props: AddViewBtnProps) {
  return <div className="d-flex align-items-center justify-content-center h-100">
    <div className="d-flex flex-column">
      <button
        onClick={props.handleClick}
        type="button"
        className="btn btn-success align-self-center"
      >
        {ADD_NEW_VIEW_BTN}
      </button>
    </div>
  </div>
}
