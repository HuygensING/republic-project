export class PersonFunction {
  id: number;
  name: string

  /**
   * People that held the position
   */
  people: number[];

  constructor(id: number, name: string, people: number[]) {
    this.id = id;
    this.name = name;
    this.people = people;
  }

}
