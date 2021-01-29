import GnbElasticClient from "../../elastic/GnbElasticClient";
import {Typeahead} from "react-bootstrap-typeahead";
import React, {useState} from "react";
import {Person, toName} from "../../elastic/model/Person";
import {PersonOption} from "../PersonOption";
import {PersonType} from "../../elastic/model/PersonType";

type PeopleTypeaheadProps = {
  id: string;
  client: GnbElasticClient,
  placeholder:string,
  personType: PersonType,
  handleSubmit: (selected: PersonOption[]) => Promise<void>
}

export default function PeopleTypeahead (props: PeopleTypeaheadProps) {

  const [fieldState, setFieldState] = useState({
    inputField: '',
    loading: true,
    options: []
  });

  const ref = React.createRef<Typeahead<any>>();

  if (fieldState.loading) {
    handleLoading();
  }

  async function handleLoading() {
    const options = await createOptions();
    setFieldState({
      ...fieldState,
      options,
      loading: false
    });
  }

  async function createOptions() {
    const found = await props.client.peopleResource.aggregateBy(fieldState.inputField, props.personType);
    if (found.length === 0) {
      return [];
    }
    const people = await props.client.peopleResource.getMulti(found.map((f: any) => f.key));
    return found.map((f: any) => {
      const person = people.find(p => p.id === f.key) || {id: found.key} as Person;
      const name = person ? toName(person) : f.name
      const total = f.sum_people_name.buckets.reduce((a: number, bucket: any) => a += bucket.doc_count, 0);
      return new PersonOption(f.key, name, total, person);
    });
  }

  function handleInputChange() {
    setFieldState({
      ...fieldState,
      loading: true,
      inputField: ref.current?.getInput().value ? ref.current?.getInput().value.toLowerCase() : ''
    });
  }

  return <Typeahead
    ref={ref}
    multiple
    onChange={props.handleSubmit}
    options={fieldState.loading ? [] : fieldState.options}
    labelKey={option => `${option.name} (${option.total})`}
    onInputChange={handleInputChange}
    placeholder={props.placeholder}
    id={props.id}
  />
}

// Update typescript definitions with public getInput-method: https://stackoverflow.com/a/64579324
declare module "react-bootstrap-typeahead" {
  interface Typeahead<T extends TypeaheadModel> extends React.Component<TypeaheadProps<T>> {
    getInput(): HTMLInputElement;
  }
}
