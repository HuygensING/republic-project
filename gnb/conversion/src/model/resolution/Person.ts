import StringUtil from "../../convert/StringUtil";

export class Person {

  public id: number;

  /**
   * Person can be:
   * an 'attendant' (present in attendance list)
   * or 'mentioned' (as mentioned in the text of a resolution)
   */
  public type: string;

  public province: string;
  public name: string;

  /**
   * Attendants can be president
   */
  public president: boolean;

  constructor(id: number, type: string, province: string, name: string, president: boolean) {
    this.id = id;
    this.type = type;
    this.province = province;
    this.president = president;
    this.name = StringUtil.clean(name);
  }
}
