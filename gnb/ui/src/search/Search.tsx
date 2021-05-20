import React from "react";
import StartEndFormField from "./field/StartEndFormField";
import FullTextFormField from "./field/FullTextFormField";
import MentionedFormField from "./field/MentionedFormField";
import AttendantsFormField from "./field/AttendantsFormField";
import Help from "../content/Help";
import PlaceFormField from "./field/PlaceFormField";
import FunctionFormField from "./field/FunctionFormField";
import FunctionCategoryFormField from "./field/FunctionCategoryFormField";
import Export from "../export/Export";
import {useLoadingContext} from "../LoadingContext";

export function Search() {
  const loading = useLoadingContext().loadingState.loading;

  return (
    <div className="row">
      <div className="col">
        <form>
          <fieldset disabled={loading}>
            <div className="form-row">
              <div className="col form-group">
                <AttendantsFormField/>
              </div>
              <div className="col form-group">
                <MentionedFormField/>
              </div>
              <div className="col form-group">
                <FunctionFormField/>
              </div>
            </div>
            <div className="form-row">
              <div className="col form-group">
                <FullTextFormField/>
              </div>
              <div className="col form-group">
                <PlaceFormField/>
              </div>
              <div className="col form-group">
                <FunctionCategoryFormField/>
              </div>
            </div>
            <div className="form-row">
              <div className="col form-group">
                <StartEndFormField/>
              </div>
              <div className="col">
                <div className="form-group float-right row mr-1">
                  <div><Export/></div>
                </div>
              </div>
            </div>
          </fieldset>
        </form>
      </div>
      <Help/>
    </div>
  );
}
