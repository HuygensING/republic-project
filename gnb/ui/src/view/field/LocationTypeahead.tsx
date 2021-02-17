import {Typeahead} from "react-bootstrap-typeahead";
import React, {useState} from "react";
import {useAsyncError} from "../../hook/useAsyncError";
import {LocationOption} from "./LocationOption";
import {useClientContext} from "../../search/ClientContext";

type LocationTypeaheadProps = {
  name: string;
  placeholder: string,
  handleSubmit: (selected: LocationOption[]) => Promise<void>
}

export default function LocationTypeahead(props: LocationTypeaheadProps) {

  const client = useClientContext().clientState.client;

  const [state, setState] = useState({
    inputField: '',
    loading: true,
    options: []
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
      const total = f.sum_annotation.buckets.reduce((a: number, bucket: any) => a += bucket.doc_count, 0);
      return new LocationOption(f.key, total);
    });
  }

  function handleInputChange() {
    setState({
      ...state,
      loading: true,
      inputField: ref.current?.getInput().value ? ref.current?.getInput().value.toLowerCase() : ''
    });
  }

  return <Typeahead
    ref={ref}
    multiple
    onChange={props.handleSubmit}
    options={state.loading ? [] : state.options}
    labelKey={option => `${option.name} (${option.total}x)`}
    onInputChange={handleInputChange}
    placeholder={props.placeholder}
    id={props.name}
  />
}

