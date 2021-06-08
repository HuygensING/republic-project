import {Client} from 'elasticsearch'
import * as fs from "fs";
import {CafDoc} from "../../import/model/CafDoc";


export default class CafEsClient {

  private client;
  private index: string;

  constructor(host: string, index: string) {
    this.index = index;
    this.client = new Client({
      host: host
    });
  }

  /**
   * Scroll example, see: https://www.elastic.co/guide/en/elasticsearch/client/javascript-api/current/scroll_examples.html
   */
  async getAll(): Promise<CafDoc[]> {
    const result: CafDoc[] = [];
    const responseQueue = [];

    const scrollResponse = await this.client.search({
      index: this.index,
      scroll: '30s',
      size: 1000,
      _source: ['metadata.id'],
      body: {
        query: {
          match_all: {}
        }
      }
    });

    responseQueue.push(scrollResponse)
    let hitCounter = 0;
    while (responseQueue.length) {
      const shiftResponse = responseQueue.shift()

      shiftResponse.hits.hits.forEach(function (hit) {
        console.log(`Handling caf doc ${++hitCounter}`);
        result.push({id: hit._source.metadata.id} as CafDoc);
      });

      if (shiftResponse.hits.total.value === result.length) {
        return result;
      }

      responseQueue.push(
        await this.client.scroll({
          scrollId: shiftResponse._scroll_id,
          scroll: '30s'
        })
      )
    }
  }

}

