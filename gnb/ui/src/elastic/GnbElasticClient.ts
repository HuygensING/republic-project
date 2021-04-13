import {Client} from 'elasticsearch';
import ResolutionResource from "./resource/ResolutionResource";
import PeopleResource from "./resource/PeopleResource";
import PlaceResource from "./resource/PlaceResource";
import FunctionResource from "./resource/FunctionResource";

export default class GnbElasticClient {

  private readonly esClient: Client;
  private readonly _resolutionResource: ResolutionResource;
  private readonly _peopleResource: PeopleResource;
  private readonly _placeResource: PlaceResource;
  private readonly _functionResource: FunctionResource;

  constructor(host: string) {

    this.esClient = new Client({
      host: host,
      log: 'info',
      apiVersion: '7.x'
    });

    this._resolutionResource = new ResolutionResource(this.esClient);
    this._peopleResource = new PeopleResource(this.esClient);
    this._placeResource = new PlaceResource(this.esClient);
    this._functionResource = new FunctionResource(this.esClient);
  }

  get resolutionResource(): ResolutionResource {
    return this._resolutionResource;
  }

  get peopleResource(): PeopleResource {
    return this._peopleResource;
  }

  get placeResource(): PlaceResource {
    return this._placeResource;
  }

  get functionResource(): FunctionResource {
    return this._functionResource;
  }

}
