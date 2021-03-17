import {Agg} from "./Agg";

export class AggImpl implements Agg {

  protected _name: string;
  protected _agg: any;

  constructor(name: string) {
    this._name = name;
  }

  addAgg(agg: Agg): void {
    this._agg.aggs[agg.name()] = agg.agg()
  }

  agg(): any {
    return this._agg;
  }

  name(): string {
    return this._name;
  }

}
