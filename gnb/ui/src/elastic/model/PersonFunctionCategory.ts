export class PersonFunctionCategory {
  name: string

  /**
   * People that held a function within this category
   */
  people: number[];

  constructor(name: string, people: number[]) {
    this.name = name;
    this.people = people;
  }

}
