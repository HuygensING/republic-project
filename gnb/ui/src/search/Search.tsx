import React from "react";
import StartEndFormField from "./field/StartEndFormField";
import FullTextFormField from "./field/FullTextFormField";
import MentionedFormField from "./field/MentionedFormField";
import AttendantsFormField from "./field/AttendantsFormField";
import SearchHelp from "./SearchHelp";
import GnbElasticClient from "../elastic/GnbElasticClient";

type SearchProps = {
  client: GnbElasticClient
};

export function Search(props: SearchProps) {

  return (
    <div className="row">
      <div className="col">
        <form>
          <div className="form-row">
            <div className="col">
              <AttendantsFormField client={props.client}/>
            </div>
            <div className="col">
              <MentionedFormField client={props.client}/>
            </div>
          </div>
          <div className="form-row">
            <div className="col">
              <FullTextFormField/>
            </div>
            <div className="col">
              <StartEndFormField/>
            </div>
          </div>
        </form>
      </div>
      <SearchHelp/>
    </div>
  );
}
