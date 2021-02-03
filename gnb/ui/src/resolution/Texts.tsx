import GnbElasticClient from "../elastic/GnbElasticClient";
import React, {useState} from "react";
import Resolution from "../elastic/model/Resolution";
import Modal from "../common/Modal";
import {RESOLUTIONS_TITLE} from "../Placeholder";
import {useAsyncError} from "../hook/useAsyncError";
import {usePrevious} from "../hook/usePrevious";
import {equal} from "../util/equal";

type TextsProps = {
  client: GnbElasticClient,
  resolutions: string[],
  isOpen: boolean,
  handleClose: () => void
}

export default function Texts(props: TextsProps) {

  const prevResolutions = usePrevious(props.resolutions);
  const [resolutions, setResolutions] = useState([] as Resolution[]);

  const stateChanged = !equal(prevResolutions, props.resolutions);
  const throwError = useAsyncError();

  if (stateChanged) {
    createResolutions();
  }

  async function createResolutions() {
    let newResolutions = await props.client.resolutionResource
      .getMulti(props.resolutions)
      .catch(throwError);

    newResolutions = newResolutions.sort((a: any, b: any) => {
      const getResolutionIndex = (id: any) => parseInt(id.split('-').pop());
      return getResolutionIndex(a.id) - getResolutionIndex(b.id);
    });
    setResolutions(newResolutions);
  }

  return (
    <Modal
      title={`${RESOLUTIONS_TITLE} (n=${resolutions.length})`}
      isOpen={props.isOpen}
      handleClose={props.handleClose}
    >
      {resolutions.map((r: any, i: number) => {
        return <div key={i}>
          <h5>{r.id}</h5>
          <div dangerouslySetInnerHTML={{__html: r.resolution.originalXml}}/>
        </div>;
      })}
    </Modal>
  );

}
