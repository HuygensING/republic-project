import {Typeahead} from "react-bootstrap-typeahead";
import React, {useState} from "react";
import {useAsyncError} from "../hook/useAsyncError";
import {useClientContext} from "../elastic/ClientContext";

type FunctionTypeaheadProps = {
  id: string;
  placeholder: string,
  handleSubmit: (selected: FunctionOption[]) => Promise<void>
}

export default function FunctionTypeahead(props: FunctionTypeaheadProps) {

  const client = useClientContext().clientState.client;

  const [state, setState] = useState({
    inputField: '',
    loading: true,
    options: [] as FunctionOption[],
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
    const found = await client.functionResource
      .aggregateBy(state.inputField)
      .catch(throwError);
    if (found.length === 0) {
      return [];
    }
    return found.map((f: any) => {
      return new FunctionOption(f.key, f.function_name.buckets[0].key, f.doc_count);
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

export class FunctionOption {
  public id: number;
  public name: string;
  public total: number;

  constructor(id: number, name: string, total: number) {
    this.id = id;
    this.name = name;
    this.total = total;
  }
}
