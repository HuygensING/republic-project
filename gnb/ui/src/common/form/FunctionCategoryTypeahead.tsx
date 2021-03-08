import {Typeahead} from "react-bootstrap-typeahead";
import React, {useState} from "react";
import {useAsyncError} from "../../hook/useAsyncError";
import {useClientContext} from "../../elastic/ClientContext";
import {PEOPLE} from "../../content/Placeholder";
import {PersonFunctionCategory} from "../../elastic/model/PersonFunctionCategory";

type FunctionCategoryTypeaheadProps = {
  id: string;
  placeholder: string,
  handleSubmit: (selected: FunctionCategoryOption[]) => Promise<void>
}

export default function FunctionCategoryTypeahead(props: FunctionCategoryTypeaheadProps) {

  const client = useClientContext().clientState.client;

  const [state, setState] = useState({
    inputField: '',
    loading: true,
    allOptions: [] as FunctionCategoryOption[],
    options: [] as FunctionCategoryOption[],
  });

  const ref = React.createRef<Typeahead<any>>();

  const throwError = useAsyncError();

  if (state.loading) {
    handleLoading();
  }

  async function handleLoading() {
    const allOptions = state.allOptions.length
      ? state.allOptions
      : await createAllOptions();

    const options = await createOptions(allOptions);

    setState({
      ...state,
      allOptions,
      options,
      loading: false
    });
  }

  async function createAllOptions() {
    const found = await client.functionResource
      .aggregateCategoriesBy(state.inputField)
      .catch(throwError);

    if (found.length === 0) {
      return [];
    }

    return found.map((f: any) => {
      const functionCategory = f.key;
      const people = f.unnest_functions.people.buckets.map((p: any) => p.key);
      return new FunctionCategoryOption(f.key, functionCategory, f.doc_count, people);
    });

  }

  async function createOptions(allOptions: FunctionCategoryOption[]) : Promise<FunctionCategoryOption[]> {
    return allOptions.filter(
      o => o.name.toLowerCase().includes(state.inputField.toLowerCase())
    );
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
    labelKey={option => `${option.name} (${option.total} ${PEOPLE})`}
    onInputChange={handleInputChange}
    placeholder={props.placeholder}
    id={props.id}
  />
}

export class FunctionCategoryOption {

  public name: string;
  public total: number;
  public personFunctionCategory: PersonFunctionCategory;

  constructor(
    id: number,
    name: string,
    total: number,
    people: number[]
  ) {

    this.name = name;
    this.total = total;

    this.personFunctionCategory = {
      name,
      people: people
    } as PersonFunctionCategory;

  }

}
