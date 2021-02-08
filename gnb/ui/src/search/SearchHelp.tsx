import React from 'react';
import {
  HELP_FULL_TEXT_BODY,
  HELP_FULL_TEXT_TITLE,
  HELP_PEOPLE_BODY,
  HELP_PEOPLE_TITLE, HELP_START_END_BODY, HELP_START_END_TITLE,
  HELP_TITLE
} from "../Placeholder";
import Modal from "../common/Modal";

export default function SearchHelp() {

  const [isOpen, setIsOpen] = React.useState(false);

  function openModal(e: any) {
    setIsOpen(true);
  }

  return (
    <>
      <button className="btn btn-outline-info search-help-btn mt-3 mr-3" type="button" onClick={openModal}>Help</button>
      <Modal isOpen={isOpen} handleClose={() => setIsOpen(false)} title={HELP_TITLE}>
        <h3>{HELP_PEOPLE_TITLE}</h3>
        <p>{HELP_PEOPLE_BODY}</p>
        <h3>{HELP_FULL_TEXT_TITLE}</h3>
        <p dangerouslySetInnerHTML={{__html: HELP_FULL_TEXT_BODY}}/>
        <h3>{HELP_START_END_TITLE}</h3>
        <p>{HELP_START_END_BODY}</p>
      </Modal>
    </>
  );
}
