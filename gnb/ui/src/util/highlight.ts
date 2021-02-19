import {Person} from "../elastic/model/Person";
import Place from "../view/model/Place";

/**
 * Util methods to highlight entities in xml using dom manipulation
 */
const domParser = new DOMParser();

export function toDom(xml: string): Document {
  return domParser.parseFromString(xml, 'text/xml');
}

export function toStr(xml: Document): string {
  return xml.documentElement.outerHTML;
}

export function highlightMentioned(dom: Document, mentioned: Person[]) {
  for (const m of mentioned) {
    const found = dom.querySelectorAll(`[idnr="${m.id}"]`)?.item(0);
    if (found) {
      found.setAttribute('class', 'highlight');
    }
  }
}

export function highlightPlaces(dom: Document, places: Place[]) {
  const found = dom.getElementsByTagName('plaats');
  for (const p of places) {
    for (const f of found) {
      if (f.textContent?.toLowerCase() === p.val.toLowerCase()) {
        f.setAttribute('class', 'highlight');
      }
    }
  }
}

