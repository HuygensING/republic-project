import GnbElasticClient from "../elastic/GnbElasticClient";
import React, {useState} from "react";
import Resolution from "../elastic/model/Resolution";
import Modal from "./Modal";
import {RESOLUTIONS_TITLE} from "../Placeholder";
import {useAsyncError} from "../hook/useAsyncError";
import {usePrevious} from "../hook/usePrevious";
import {equal} from "../util/equal";
import {PersonType} from "../elastic/model/PersonType";
import {PersonAnn} from "../elastic/model/PersonAnn";
import {useSearchContext} from "../search/SearchContext";
import {joinJsx} from "../util/joinJsx";
import {Person} from "../elastic/model/Person";

type TextsProps = {
  client: GnbElasticClient,
  resolutions: string[],
  isOpen: boolean,
  handleClose: () => void
}

const domParser = new DOMParser();

export default function Texts(props: TextsProps) {

  const prevResolutions = usePrevious(props.resolutions);
  const [resolutions, setResolutions] = useState([] as Resolution[]);
  const {searchState} = useSearchContext();
  const stateChanged = !equal(prevResolutions, props.resolutions);

  const throwError = useAsyncError();

  if (stateChanged) {
    createResolutions();
  }

  async function createResolutions() {
    let newResolutions = await props.client.resolutionResource
      .getMulti(props.resolutions, searchState.fullText)
      .catch(throwError);

    newResolutions = newResolutions.sort((a: any, b: any) => {
      const getResolutionIndex = (id: any) => parseInt(id.split('-').pop());
      return getResolutionIndex(a.id) - getResolutionIndex(b.id);
    });
    setResolutions(newResolutions);
  }

  const attendantIds = searchState.attendants.map(a => a.id);

  return (
    <Modal
      title={`${RESOLUTIONS_TITLE} (n=${resolutions.length})`}
      isOpen={props.isOpen}
      handleClose={props.handleClose}
    >
      {resolutions.map((r: any, i: number) => {

        r.resolution.originalXml = highlightMentioned(r.resolution.originalXml, searchState.mentioned);

        return <div key={i}>
          <h5>{r.id}</h5>
          <small><strong>Aanwezigen</strong>: {r.people
            .filter((p: PersonAnn) => p.type === PersonType.ATTENDANT)
            .map((p: PersonAnn, i: number) => {
              const isAttendant = attendantIds.includes(p.id);
              return <span key={i} className={isAttendant ? 'highlight' : ''}>{p.name} (ID {p.id})</span>
            })
            .reduce(joinJsx)
          }</small>
          <div dangerouslySetInnerHTML={{__html: r.resolution.originalXml}}/>
        </div>;

      })}
    </Modal>
  );

}

function highlightMentioned(originalXml: string, mentioned: Person[]) {
  if (mentioned.length === 0) {
    return originalXml;
  }

  const dom = domParser.parseFromString(originalXml, 'text/xml');

  for (const m of mentioned) {
    const found = dom.querySelectorAll(`[idnr="${m.id}"]`)?.item(0);
    if (found) {
      found.setAttribute('class', 'highlight');
    }
  }

  return dom.documentElement.outerHTML;
}
