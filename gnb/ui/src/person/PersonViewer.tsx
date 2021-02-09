import React, {useEffect, useRef, useState} from "react";
import GnbElasticClient from "../elastic/GnbElasticClient";
import TextsModal from "../common/Texts";
import {D3Canvas} from "../common/D3Canvas";
import PersonHistogram from "./PersonHistogram";
import {Person} from "../elastic/model/Person";
import {PersonType} from "../elastic/model/PersonType";
import DeleteButton from "./DeleteButton";
import useHover from "../hook/useHover";

type PersonViewerProps = {
  client: GnbElasticClient,
  person: Person,
  type: PersonType
  onDelete: () => void;
}

export default function PersonViewer(props: PersonViewerProps) {

  const svgRef = useRef(null);
  const [hasSvg, setHasSvg] = useState(svgRef.current);

  // TODO: prevent rerendering (and fetching of es resources) on every hover
  const deleteRef = useRef(null)
  const isHovering = useHover(deleteRef);

  useEffect(() => {
    setHasSvg(svgRef.current)
  }, [svgRef]);

  const [state, setState] = React.useState({
    ids: [] as string[],
    showTexts: false,
    isMarked: false
  });

  return <div className="row mt-3">
    <div className="col">
      <div className={`border border-white ${isHovering ? 'bg-light' : ''}`}>

        <DeleteButton
          hoverRef={deleteRef}
          onClose={props.onDelete}
        />

        <D3Canvas svgRef={svgRef}/>

        {hasSvg ? <PersonHistogram
          handleResolutions={(ids: string[]) => setState({...state, ids, showTexts: true})}
          client={props.client}
          svgRef={svgRef}
          person={props.person}
          type={props.type}
        /> : null}

        <TextsModal
          client={props.client}
          resolutions={state.ids}
          isOpen={state.showTexts}
          handleClose={() => setState({...state, showTexts: false})}
        />

      </div>
    </div>
  </div>;

}
