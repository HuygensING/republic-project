import React, {memo, useState} from "react";
import Resolution from "../../elastic/model/Resolution";
import Modal from "../Modal";
import {RESOLUTIONS_TEXTS_TITLE} from "../../content/Placeholder";
import {useAsyncError} from "../../hook/useAsyncError";
import {equal} from "../../util/equal";
import {SearchStateType, useSearchContext} from "../../search/SearchContext";
import {useClientContext} from "../../elastic/ClientContext";
import {Text} from "./Text";

type TextsProps = {
  resolutions: string[],
  handleClose: () => void,

  /**
   * Ids of attendants to highlight
   */
  highlightAttendants?: number[]

  /**
   * Query_string query to highlight originalXml using elasticsearch highlighting
   */
  highlightQuery?: string

  /**
   * Function to highlight resolution.originalXml
   * To highlight something: add the class name 'highlight'
   */
  highlightXml?: (originalXml: string) => string

  memoKey: any
}

export const Texts = memo(function (props: TextsProps) {

  const client = useClientContext().clientState.client;
  const {searchState} = useSearchContext();

  const [state, setState] = useState({
    resolutions: [] as Resolution[],
    hasLoaded: false
  });

  const throwError = useAsyncError();

  if (!state.hasLoaded) {
    let fullTextHighlight = searchState.fullText;
    if (props.highlightQuery) {
      fullTextHighlight += ' ' + props.highlightQuery;
    }
    client.resolutionResource
      .getMulti(props.resolutions, fullTextHighlight)
      .then((results) => {
        results = sortResolutions(results);
        setState({resolutions: results, hasLoaded: true});
      })
      .catch(throwError);
  }

  const {mentionedToHighlight, attendantsToHighlight} = combinePeopleToHighlight(searchState, props);

  return (
    <Modal
      title={`${RESOLUTIONS_TEXTS_TITLE} (${state.resolutions.length})`}
      isOpen={true}
      handleClose={props.handleClose}
    >
      {state.hasLoaded ? state.resolutions.map((r: any, i: number) =>
        <Text
          key={i}
          resolution={r}
          attendantsToHighlight={attendantsToHighlight}
          mentionedToHighlight={mentionedToHighlight}
          highlightXml={props.highlightXml}
        />
      ) : 'Loading...'}
    </Modal>
  );

}, (prev, next) => equal(prev.memoKey, next.memoKey))


function sortResolutions(newResolutions: Resolution[]) {
  newResolutions = newResolutions.sort((a: any, b: any) => {
    const getResolutionIndex = (id: any) => parseInt(id.split('-').pop());
    return getResolutionIndex(a.id) - getResolutionIndex(b.id);
  });
  return newResolutions;
}


/**
 * Combine attendants and mentioned from search context and Texts props
 */
function combinePeopleToHighlight(searchState: SearchStateType, props: TextsProps) {
  // Deduplicate people IDs:
  const peopleToHighlight = Array.from(new Set(([] as number[]).concat(
    ...searchState.functions.map(f => f.people)).concat(
    ...searchState.functionCategories.map(f => f.people))
  ));

  const mentionedToHighlight: number[] = [...searchState.mentioned.map(m => m.id), ...peopleToHighlight];
  const attendantsToHighlight: number[] = [...searchState.attendants.map(a => a.id), ...peopleToHighlight];

  if (props.highlightAttendants) {
    attendantsToHighlight.push(...props.highlightAttendants);
  }

  return {mentionedToHighlight, attendantsToHighlight};
}
