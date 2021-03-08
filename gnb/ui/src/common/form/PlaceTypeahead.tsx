import {Typeahead} from "react-bootstrap-typeahead";
import React, {useState} from "react";
import {useAsyncError} from "../../hook/useAsyncError";
import {useClientContext} from "../../elastic/ClientContext";

type PlaceTypeaheadProps = {
  id: string;
  placeholder: string,
  handleSubmit: (selected: PlaceOption[]) => Promise<void>
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

  return <Typeahead
    ref={ref}
    multiple
    onChange={props.handleSubmit}
    options={state.loading ? [] : state.options}
    filterBy={() => true}
    labelKey={option => `${option.name} (${option.total}x)`}
    onInputChange={handleInputChange}
    placeholder={props.placeholder}
    id={props.id}
  />
}

export class PlaceOption {
  public name: string;
  public total: number;

  constructor(name: string, total: number) {
    this.name = name;
    this.total = total;
  }
}
