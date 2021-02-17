import {Client} from 'elasticsearch';
import ResolutionResource from "./ResolutionResource";
import PeopleResource from "./PeopleResource";
import PlaceResource from "./PlaceResource";

export default class GnbElasticClient {

  private esClient: Client;
  private _resolutionResource: ResolutionResource;
  private _peopleResource: PeopleResource;
  private _placeResource: PlaceResource;

  constructor(host: string) {

    this.esClient = new Client({
      host: host,
      log: 'info',
      apiVersion: '7.x'
    });

    this._resolutionResource = new ResolutionResource(this.esClient);
    this._peopleResource = new PeopleResource(this.esClient);
    this._placeResource = new PlaceResource(this.esClient);
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

}
