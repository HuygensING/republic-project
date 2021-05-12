import {useLoading} from "./LoadingContext";
import React from "react";

export function Header() {
  return <div className="row mt-3 mb-3">
    <div className="col">
      <h1>
        GNB
        <small
          className="text-muted"
        >
          &nbsp;
          Governance, Netwerken en Besluitvorming in de Staten-Generaal
          &nbsp;
          {useLoading() ? <i className="main-loader fas fa-sync fa-spin ml-3"/> : null}
        </small>

      </h1>
    </div>
  </div>

}
