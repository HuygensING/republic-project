import {Person} from "../elastic/model/Person";

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
