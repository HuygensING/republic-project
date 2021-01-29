import {Client} from 'elasticsearch';
import ResolutionResource from "./ResolutionResource";
import PeopleResource from "./PeopleResource";

export default class GnbElasticClient {

  private esClient: Client;
  private _resolutionResource: ResolutionResource;
  private _peopleResource: PeopleResource;

  constructor(host: string) {

    this.esClient = new Client({
      host: host,
      log: 'info',
      apiVersion: '7.x'
    });

    this._resolutionResource = new ResolutionResource(this.esClient);
    this._peopleResource = new PeopleResource(this.esClient);
  }

  get resolutionResource(): ResolutionResource {
    return this._resolutionResource;
  }

  get peopleResource(): PeopleResource {
    return this._peopleResource;
  }

}
