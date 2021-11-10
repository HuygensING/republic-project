import StringUtil from "../../convert/StringUtil";

export class Annotation {
  public id: number;
  public name: string;
  public value: string;

  constructor(id: number, name: string, value: string) {
    this.id = id;
    this.name = name;
    this.value = StringUtil.clean(value);
  }
}
