import {Typeahead} from "react-bootstrap-typeahead";
import React, {useState} from "react";
import {useAsyncError} from "../../hook/useAsyncError";
import {useClientContext} from "../../elastic/ClientContext";
import {PEOPLE} from "../../content/Placeholder";
import {PersonFunction} from "../../elastic/model/PersonFunction";
import {useLoading} from "../../LoadingContext";

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
      .aggregateByName(state.inputField)
      .catch(throwError);
    if (found.length === 0) {
      return [];
    }
    return found.map((f: any) => {
      const functionName = f.function_name.buckets[0].key;
      const people = f.function_name.buckets[0].unnest_functions.people.buckets.map((p: any) => p.key);
      return new FunctionOption(f.key, functionName, f.doc_count, people);
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
    disabled={useLoading()}
    ref={ref}
    multiple
    onChange={props.handleSubmit}
    options={state.loading ? [] : state.options}
    filterBy={() => true}
    labelKey={option => `${option.name} (${option.total} ${PEOPLE})`}
    onInputChange={handleInputChange}
    placeholder={props.placeholder}
    id={props.id}
  />
}

export class FunctionOption {

  public id: number;
  public name: string;
  public total: number;
  public personFunction: PersonFunction;

  constructor(
    id: number,
    name: string,
    total: number,
    people: number[]
  ) {

    this.id = id;
    this.name = name;
    this.total = total;

    this.personFunction = {
      id,
      name,
      people: people
    } as PersonFunction;

  }

}
