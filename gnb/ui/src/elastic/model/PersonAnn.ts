import {PersonType} from "./PersonType";

export type PersonAnn = {
  id: number;
  type: PersonType;
  province?: string;
  name: string;
  president: boolean
}
