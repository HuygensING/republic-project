import Config from "../Config";
import * as elasticsearch from "elasticsearch";
import EsDocument from "../model/EsDocument";

export default class EsService {

  private esIds: string[] = []

  private esClient = new elasticsearch.Client({
    host: Config.ES_HOST,
    apiVersion: Config.ES_VERSION,
    log: 'info'
  });

  public async createEsDoc(index: string, esDoc: EsDocument): Promise<any> {
    if (this.esIds.includes(esDoc.id)) {
      throw new Error(`Id ${esDoc.id} already exists`);
    }
    this.esIds.push(esDoc.id);
    return await this.esClient.create({
      index: index,
      type: '_doc',
      body: esDoc,
      id: esDoc.id
    });
  }
}
