import Modal from "../common/Modal";
import {useState} from "react";
import {EXPORT_BUTTON, EXPORT_DESCRIPTION, EXPORT_DOWNLOAD_LINKS} from "../content/Placeholder";
import {useResolutionContext} from "../resolution/ResolutionContext";
import {HistogramBar} from "../common/plot/Histogram";
import {useClientContext} from "../elastic/ClientContext";
import {PersonAnn} from "../elastic/model/PersonAnn";
import {PersonType} from "../elastic/model/PersonType";
import Resolution from "../elastic/model/Resolution";
import {useSearchContext} from "../search/SearchContext";
import {useViewContext} from "../view/ViewContext";
import {ViewType} from "../view/model/ViewType";
import {Person} from "../elastic/model/Person";
import {PersonFunction} from "../elastic/model/PersonFunction";
import {PersonFunctionCategory} from "../elastic/model/PersonFunctionCategory";

const downloadDataType = 'data:text/plain;charset=utf-8,';
const NODES_FILENAME = 'nodes.csv';
const EDGES_FILENAME = 'edges.csv';

type Node = {
  id: number,
  label: string,
  type: NodeType
};

enum NodeType {
  NONE = '',
  SEARCHED = 'searched',
  PLOTTED = 'plotted',
}

type Edge = {
  source: number,
  target: number,
  label: EdgeLabel,
  weight: number,
  type: EdgeType
}

enum EdgeLabel {
  ATTENDANT_ATTENDANT = 'attendant-attendant',
  ATTENDANT_MENTIONED = 'attendant-mentioned',
  MENTIONED_MENTIONED = 'mentioned-mentioned',
}

enum EdgeType {
  DIRECTED = 'directed',
  UNDIRECTED = 'undirected'
}

export default function Export() {

  const [state, setState] = useState({
    isOpen: false,
    nodes: '',
    edges: ''
  });

  const {resolutionState} = useResolutionContext();
  const {searchState} = useSearchContext();
  const {viewState} = useViewContext();
  const {client} = useClientContext().clientState;

  async function startCreatingContents() {
    const {nodes, edges} = await createContents();
    setState(s => {
      return {...s, nodes, edges}
    });
  }

  async function createContents(): Promise<{ nodes: string, edges: string }> {

    const resolutionIds = resolutionState.resolutions
      .reduce((all, arr: HistogramBar) => all.concat(arr.ids), [] as string[]);

    const resolutions = await client.resolutionResource.getMulti(resolutionIds);

    const peopleIds = [...new Set(resolutions.reduce(
      (all, arr: any) => all.concat(arr.people.map((p: any) => p.id)), [] as number[])
    )];

    const people = await client.peopleResource.getMulti(peopleIds);

    const peopleSearched = [...new Set(searchState.attendants.map(a => a.id)
      .concat(searchState.mentioned.map(m => m.id))
      .concat(searchState.functions.reduce((all, f) => all.concat(f.people), [] as number[]))
      .concat(searchState.functionCategories.reduce((all, fc) => all.concat(fc.people), [] as number[])))];

    const peoplePlotted = [...new Set(viewState.views
      .filter(v => [ViewType.MENTIONED, ViewType.ATTENDANT].includes(v.type))
      .map(v => (v.entity as Person).id)
      .concat(
        viewState.views
          .filter(v => v.type === ViewType.FUNCTION)
          .reduce((all, v) => all.concat((v.entity as PersonFunction).people), [] as number[])
      ).concat(
        viewState.views
          .filter(v => v.type === ViewType.FUNCTION_CATEGORY)
          .reduce((all, v) => all.concat((v.entity as PersonFunctionCategory).people), [] as number[])
      ))];

    const nodes = [] as Node[];
    const edges = [] as Edge[];
    for (const r of resolutions) {
      // All edges added by this resolution
      const resolutionEdges = [] as Edge[];
      for (const p1 of r.people) {
        handleNode(p1);
        handleEdgesOfNode(r, resolutionEdges, p1);
      }
    }

    let nodesString = 'Id;Label;Type\n';
    for (const n of nodes) {
      nodesString += `${n.id};${n.label};${n.type}\n`
    }

    let edgesString = 'Source;Target;Label;Weight;Type\n';
    for (const e of edges) {
      edgesString += `${e.source};${e.target};${e.label};${e.weight};${e.type}\n`
    }

    let nodesEncoded = downloadDataType + encodeURIComponent(nodesString);
    let edgesEncoded = downloadDataType + encodeURIComponent(edgesString);
    return {nodes: nodesEncoded, edges: edgesEncoded};

    function handleNode(p: PersonAnn) {
      const found = nodes.find(n => n.id === p.id);
      if (!found) {
        const label = people.find(p2 => p2 && p2.id === p.id)?.searchName;
        const node = {id: p.id, label: label ? label : 'id-' + p.id} as Node;

        if (peoplePlotted.includes(node.id)) {
          node.type = NodeType.PLOTTED;
        } else if (peopleSearched.includes(node.id)) {
          node.type = NodeType.SEARCHED;
        } else {
          node.type = NodeType.NONE;
        }

        nodes.push(node);
      }
    }

    function handleEdgesOfNode(r: Resolution, resolutionEdges: Edge[], p1: PersonAnn) {
      for (const p2 of r.people) {
        handleEdge(p1, p2, resolutionEdges);
      }
    }

    function handleEdge(p1: PersonAnn, p2: PersonAnn, resolutionEdges: Edge[]) {
      if (p1.id === p2.id) {
        return;
      }
      const newEdge = createEdge(p1, p2);
      const added = resolutionEdges.find(byEdge(newEdge));

      if (added) {
        // Prevent doubles:
        return;
      }

      resolutionEdges.push(newEdge);
      const found = edges.find(byEdge(newEdge));

      if (found) {
        found.weight++;
      } else {
        newEdge.weight = 1;
        edges.push(newEdge);
      }

    }

    function byEdge(toCompare: Edge) {
      return function (e: Edge) {
        return e.source === toCompare.source
          && e.target === toCompare.target
          && e.label === toCompare.label
          && e.type === toCompare.type;
      }
    }

    function createEdge(p1: PersonAnn, p2: PersonAnn) {
      let label: EdgeLabel;
      let type: EdgeType;
      let sourceTarget: number[];
      if (p1.type === PersonType.ATTENDANT && p2.type === PersonType.ATTENDANT) {
        // Sort undirected edge by ID:
        label = EdgeLabel.ATTENDANT_ATTENDANT;
        type = EdgeType.UNDIRECTED;
        sourceTarget = [p1.id, p2.id].sort();
      } else if (p1.type === PersonType.MENTIONED && p2.type === PersonType.MENTIONED) {
        // Sort undirected edge by ID:
        label = EdgeLabel.MENTIONED_MENTIONED;
        type = EdgeType.UNDIRECTED;
        sourceTarget = [p1.id, p2.id].sort();
      } else {
        // Sort directed edge from attendant to mentioned:
        label = EdgeLabel.ATTENDANT_MENTIONED;
        type = EdgeType.DIRECTED;
        if (p1.type === PersonType.ATTENDANT) {
          sourceTarget = [p1.id, p2.id];
        } else {
          sourceTarget = [p2.id, p1.id];
        }
      }
      return {label, type, source: sourceTarget[0], target: sourceTarget[1]} as Edge;
    }

  }

  async function openModal() {
    setState(s => {
      return {...s, isOpen: true}
    });
    startCreatingContents();
  }

  function closeModal() {
    setState(s => {
      return {...s, isOpen: false, nodes: '', edges: ''}
    });
  }

  function renderFiles() {
    if (!state.edges || !state.nodes) {
      return <p className="mt-2"><i className="fas fa-sync fa-spin"/></p>
    }
    return <>
      <p>{EXPORT_DOWNLOAD_LINKS}</p>
      <ul>
        <li><a href={state.nodes} download={NODES_FILENAME}>{NODES_FILENAME}</a></li>
        <li><a href={state.edges} download={EDGES_FILENAME}>{EDGES_FILENAME}</a></li>
      </ul>
    </>;
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
      {renderFiles()}
    </Modal>
  </div>
}
