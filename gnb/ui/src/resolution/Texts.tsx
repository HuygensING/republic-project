import GnbElasticClient from "../elastic/GnbElasticClient";
import React, {useState} from "react";
import {equal, usePrevious} from "../Util";
import Resolution from "../elastic/model/Resolution";
import Modal from "../Modal";
import {RESOLUTIONS_TITLE} from "../Placeholder";

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

  if (stateChanged) {
    createResolutions();
  }

  async function createResolutions() {
    let newResolutions = await props.client.resolutionResource.getMulti(props.resolutions);
    newResolutions = newResolutions.sort((a: any, b: any) => {
      const getResolutionIndex = (id: any) => parseInt(id.split('-').pop());
      return getResolutionIndex(a.id) - getResolutionIndex(b.id);
    });
    setResolutions(newResolutions);
  }

  return (
    <Modal
      title={RESOLUTIONS_TITLE}
      isOpen={props.isOpen}
      handleClose={props.handleClose}
    >
      {resolutions.map((r: any, i: number) => {
        return <div key={i}>
          <h5>{r.id}</h5>
          <div dangerouslySetInnerHTML={{__html: r.resolution.originalXml}} />
        </div>;
      })}
    </Modal>
  );

}
