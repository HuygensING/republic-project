import {Typeahead, TypeaheadModel, TypeaheadProps} from "react-bootstrap-typeahead";
import React, {useState} from "react";
import {Person, toName} from "../elastic/model/Person";
import {PersonType} from "../elastic/model/PersonType";
import {useAsyncError} from "../hook/useAsyncError";
import {useClientContext} from "../elastic/ClientContext";

type PeopleTypeaheadProps = {
  id: string;
  placeholder: string,
  personType: PersonType,
  handleSubmit: (selected: PersonOption[]) => Promise<void>
}

export default function PeopleTypeahead(props: PeopleTypeaheadProps) {

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
    const found = await client.peopleResource
      .aggregateBy(state.inputField, props.personType)
      .catch(throwError);

    if (found.length === 0) {
      return [];
    }

    const people = await client.peopleResource
      .getMulti(found.map((f: any) => f.key))
      .catch(throwError);

    return found.map((f: any) => {
      const person = people.find(p => p.id === f.key) || {id: found.key} as Person;
      const name = person ? toName(person) : f.name
      const total = f.sum_people_name.buckets.reduce((a: number, bucket: any) => a += bucket.doc_count, 0);
      return new PersonOption(f.key, name, total, person);
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
    filterBy={() => true}
    onInputChange={handleInputChange}
    placeholder={props.placeholder}
    id={props.id}
  />
}

export class PersonOption {
  public id: number;
  public name: string
  public total: number;
  public person: Person;

  constructor(id: number, name: string, total: number, person: Person) {
    this.id = id;
    this.name = name;
    this.total = total;
    this.person = person;
  }
}

// Update typescript definitions with public getInput-method: https://stackoverflow.com/a/64579324
declare module "react-bootstrap-typeahead" {
  interface Typeahead<T extends TypeaheadModel> extends React.Component<TypeaheadProps<T>> {
    getInput(): HTMLInputElement;
  }
}
