import {Client} from 'elasticsearch'
import {CafDoc} from "../../import/model/CafDoc";


export default class CafEsClient {

  private client: Client;
  private index: string;

  constructor(host: string, index: string) {
    this.index = index;
    this.client = new Client({
      host: host
    });
  }

  /**
   * Retrieve docs from caf es index
   * Process each doc with handler
   * Uses scroll API: https://www.elastic.co/guide/en/elasticsearch/client/javascript-api/current/scroll_examples.html
   */
  async handleAll(
    handler: (doc: CafDoc) => Promise<void>,
    scrollTime: string = '30s',
    pageSize: number = 10
  ): Promise<void> {
    const nextScrollTime = scrollTime;
    const result: string[] = [];
    const responseQueue = [];

    const total = (await this.client.count({index: this.index, body: {}})).count;

    const scrollResponse = await this.client.search({
      index: this.index,
      scroll: scrollTime,
      size: pageSize,
      body: {
        query: {
          match_all: {}
        }
      }
    });

    responseQueue.push(scrollResponse);
    let hitCounter = 0;
    while (responseQueue.length) {
      const shiftResponse = responseQueue.shift()

      for (const hit of shiftResponse.hits.hits) {
        console.log(`Handling doc ${++hitCounter} of ${total}`);
        result.push(hit._source.metadata.id);
        await handler(hit._source as CafDoc);
      }

      if (shiftResponse.hits.total.value === result.length) {
        console.log(`Handled all`);
        return;
      }

      responseQueue.push(
        await this.client.scroll({
          scrollId: shiftResponse._scroll_id,
          scroll: scrollTime
        })
      )
    }
  }

}

