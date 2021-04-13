import React, {MutableRefObject} from "react";

type DeleteButtonProps = {
  onClose: () => void,
  hoverRef: MutableRefObject<any>
}

export default function DeleteViewButton(props: DeleteButtonProps) {

  return <button ref={props.hoverRef} onClick={props.onClose} type="button" className="delete-btn close pr-3 pt-2" aria-label="Close">
    <span aria-hidden="true">&times;</span>
  </button>;

};
