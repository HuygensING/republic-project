import {Typeahead} from "react-bootstrap-typeahead";
import React, {useState} from "react";
import {useAsyncError} from "../../hook/useAsyncError";
import {PlaceOption} from "./PlaceOption";
import {useClientContext} from "../../search/ClientContext";
import Place from "../model/Place";
import {ViewType} from "../model/ViewType";
import {PICK_PLACES} from "../../Placeholder";

type PlaceTypeaheadProps = {
  handleSubmit: (l: Place, t: ViewType) => Promise<void>
}

export default function PlaceTypeahead(props: PlaceTypeaheadProps) {

  const client = useClientContext().clientState.client;

  const [state, setState] = useState({
    inputField: '',
    loading: true,
    options: [] as PlaceOption[],
  });

  const ref = React.createRef<Typeahead<any>>();

  const throwError = useAsyncError();
  if (state.loading) {
    handleLoading();
  }

  async function handleLoading() {
    const options = await createOptions();
    setState({
      ...state,
      options,
      loading: false
    });

  }

  async function createOptions() {
    const found = await client.placeResource
      .aggregateBy(state.inputField)
      .catch(throwError);
    if (found.length === 0) {
      return [];
    }
    return found.map((f: any) => {
      return new PlaceOption(f.key, f.doc_count);
    });
  }

  function handleInputChange() {
    setState({
      ...state,
      loading: true,
      inputField: ref.current?.getInput().value ? ref.current?.getInput().value.toLowerCase() : ''
    });
  }

  function handleSubmit(options: PlaceOption[]) {
    return props.handleSubmit(new Place(options[0].name), ViewType.PLACE);
  }

  return <Typeahead
    ref={ref}
    multiple
    onChange={handleSubmit}
    options={state.loading ? [] : state.options}
    labelKey={option => `${option.name} (${option.total}x)`}
    onInputChange={handleInputChange}
    placeholder={PICK_PLACES}
    id={"place-typeahead"}
  />
}

