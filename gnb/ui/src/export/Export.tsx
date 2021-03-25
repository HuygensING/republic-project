import Modal from "../common/Modal";
import {useState} from "react";
import {EXPORT_BUTTON, EXPORT_DESCRIPTION} from "../content/Placeholder";
import {useResolutionContext} from "../resolution/ResolutionContext";
import {HistogramBar} from "../common/Histogram";
import {useClientContext} from "../elastic/ClientContext";

const downloadDataType = 'data:text/plain;charset=utf-8,';
const NODES_FILENAME = 'nodes.csv';
const EDGES_FILENAME = 'edges.csv';

type Node = {
  id: number,
  label: string
};

export default function Export() {

  const [state, setState] = useState({
    isOpen: false,
    nodes: '',
    edges: ''
  });

  const {resolutionState} = useResolutionContext();
  const client = useClientContext().clientState.client;

  async function createContents(): Promise<{ nodes: string, edges: string }> {

    const resolutionIds = resolutionState.resolutions
      .reduce((all, arr: HistogramBar) => all.concat(arr.ids), [] as string[]);

    const resolutions = await client.resolutionResource.getMulti(resolutionIds);

    const peopleIds = [...new Set(resolutions.reduce(
      (all, arr: any) => all.concat(arr.people.map((p: any) => p.id)), [] as number[])
    )];

    const people = await client.peopleResource.getMulti(peopleIds);

    const nodes = [] as Node[];
    for (const r of resolutions) {
      for (const p of r.people) {
        const found = nodes.find(n => n.id === p.id);
        if (!found) {
          const label = people.find(p2 => p2 && p2.id === p.id)?.searchName;
          const node = {id: p.id, label: label ? label : 'id-' + p.id} as Node;
          nodes.push(node)
        }
      }
    }

    let nodesString = 'Id;Label\n';
    for (const n of nodes) {
      nodesString += `${n.id};${n.label}\n`
    }

    const edgesString = 'Source;Target;Label;Weight' +
      '\n1;2;attendant-attendant;3' +
      '\n1;2;attendant-mentioned;3';

    let nodesEncoded = downloadDataType + encodeURIComponent(nodesString);
    let edgesEncoded = downloadDataType + encodeURIComponent(edgesString);
    return {nodes: nodesEncoded, edges: edgesEncoded};
  }

  async function openModal() {
    const {nodes, edges} = await createContents();
    setState(s => {
      const result = {...s, isOpen: true, nodes, edges};
      return result
    });
  }

  function closeModal() {
    setState(s => {
      return {...s, isOpen: false}
    });
  }

  return <div>
    <button
      type="button"
      onClick={openModal}
      className="btn btn-info float-right"
    >
      {EXPORT_BUTTON} <i className="fas fa-sign-out-alt"/>
    </button>
    <Modal title={EXPORT_BUTTON} isOpen={state.isOpen} handleClose={closeModal}>
      {EXPORT_DESCRIPTION}
      <ul>
        <li><a href={state.nodes} download={NODES_FILENAME}>{NODES_FILENAME}</a></li>
        <li><a href={state.edges} download={NODES_FILENAME}>{EDGES_FILENAME}</a></li>
      </ul>
    </Modal>
  </div>
}
