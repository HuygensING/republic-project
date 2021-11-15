import EsResolutionDocument from "../model/resolution/EsResolutionDocument";
import {PersonPresenceAgg} from "../PersonPresenceAgg";

export async function aggregatePeople(
  aggs: PersonPresenceAgg[],
  esDocs: EsResolutionDocument[]
): Promise<void> {
  console.log('aggregate people presence');
  for (const doc of esDocs) {
    for (const person of doc.people) {
      let agg = aggs.find(a => a.id === person.id);
      if (!agg) {
        agg = new PersonPresenceAgg();
        agg.id = person.id;
        aggs.push(agg);
        console.log('add agg ', agg.id);
      }
      if (person.type === 'attendant') {
        agg.attended++;
      } else if (person.type === 'mentioned') {
        agg.mentioned++;
      }
    }
  }
}
