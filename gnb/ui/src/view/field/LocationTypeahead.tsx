import {Typeahead} from "react-bootstrap-typeahead";
import React, {useState} from "react";
import {useAsyncError} from "../../hook/useAsyncError";
import {LocationOption} from "./LocationOption";
import {useClientContext} from "../../search/ClientContext";
import Location from "../model/Location";
import {ViewType} from "../model/ViewType";
import {PICK_LOCATIONS} from "../../Placeholder";

type LocationTypeaheadProps = {
  handleSubmit: (l: Location, t: ViewType) => Promise<void>
}

export default function LocationTypeahead(props: LocationTypeaheadProps) {

  const client = useClientContext().clientState.client;

  const [state, setState] = useState({
    inputField: '',
    loading: true,
    options: [] as LocationOption[],
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
    const found = await client.locationResource
      .aggregateBy(state.inputField)
      .catch(throwError);
    if (found.length === 0) {
      return [];
    }
    return found.map((f: any) => {
      return new LocationOption(f.key, f.doc_count);
    });
  }

  function handleInputChange() {
    setState({
      ...state,
      loading: true,
      inputField: ref.current?.getInput().value ? ref.current?.getInput().value.toLowerCase() : ''
    });
  }

  function handleSubmit(options: LocationOption[]) {
    return props.handleSubmit(new Location(options[0].name), ViewType.LOCATION);
  }

  return <Typeahead
    ref={ref}
    multiple
    onChange={handleSubmit}
    options={state.loading ? [] : state.options}
    labelKey={option => `${option.name} (${option.total}x)`}
    onInputChange={handleInputChange}
    placeholder={PICK_LOCATIONS}
    id={"location-typeahead"}
  />
}

