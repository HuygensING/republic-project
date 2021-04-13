import {MODAL_CLOSE} from "../content/Placeholder";
import React, {ReactNode} from "react";
import useEvent from "../hook/useEvent";

type ModalProps = {
  title: string
  isOpen: boolean;
  handleClose: () => void;
  children: ReactNode
}

export default function Modal(props: ModalProps) {
  useEvent('keyup', closeOnEsc);

  function closeOnEsc(e: React.KeyboardEvent<HTMLElement>) {
    if (e.key === 'Escape') {
      props.handleClose();
    }
  }

  return (
    <div>
      <div
        className={`modal fade ${props.isOpen ? 'd-block show' : 'd-none'}`}
        tabIndex={-1}
        aria-modal="true"
        role="dialog"
      >
        <div className="modal-dialog" role="document">
          <div className="modal-content">
            <div className="modal-header">
              <h2 className="modal-title">{props.title}</h2>
              <button type="button" className="close" aria-label="Close"  onClick={props.handleClose}>
                <span aria-hidden="true">&times;</span>
              </button>
            </div>
            <div className="modal-body">
              {props.children}
            </div>
            <div className="modal-footer">
              <button type="button" className="btn btn-info" onClick={props.handleClose}>{MODAL_CLOSE}</button>
            </div>
          </div>
        </div>
      </div>
      <div
        id="backdrop"
        className={`modal-backdrop fade show ${props.isOpen ? 'd-block show' : 'd-none'}`}
      />
    </div>

  );
}
