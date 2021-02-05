import React from "react";

type WarningProps = {
  msg: string,
  onClose: () => void
}

export default function Warning (props: WarningProps) {
  return <div className="container-fluid fixed-top">
    <div className="row justify-content-center">
      <div className="col-4">
        <div className="alert alert-warning m-3 text-center alert-dismissible fade show" role="alert">
          {props.msg}
          <button type="button" className="close" aria-label="Close" onClick={() => props.onClose()}>
            <span aria-hidden="true">&times;</span>
          </button>
        </div>
      </div>
    </div>
  </div>;
}
