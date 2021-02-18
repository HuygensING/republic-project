import React from "react";
import StartEndFormField from "./field/StartEndFormField";
import FullTextFormField from "./field/FullTextFormField";
import MentionedFormField from "./field/MentionedFormField";
import AttendantsFormField from "./field/AttendantsFormField";
import Help from "../content/Help";
import PlaceFormField from "./field/PlaceFormField";

export function Search() {

  return (
    <div className="row">
      <div className="col">
        <form>
          <div className="form-row">
            <div className="col form-group">
              <AttendantsFormField />
            </div>
            <div className="col form-group">
              <MentionedFormField />
            </div>
          </div>
          <div className="form-row">
            <div className="col  form-group">
              <FullTextFormField/>
            </div>
            <div className="col  form-group">
              <PlaceFormField/>
            </div>
          </div>
          <div className="form-row">
            <div className="col form-group">
              <StartEndFormField/>
            </div>
          </div>
        </form>
      </div>
      <Help/>
    </div>
  );
}
