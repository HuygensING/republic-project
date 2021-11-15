import EsResolutionDocument from "../model/resolution/EsResolutionDocument";
import {Metadata} from "../model/resolution/Metadata";
import {Meeting} from "../model/resolution/Meeting";
import XmlUtil from "./XmlUtil";
import {Resolution} from "../model/resolution/Resolution";
import {Annotation} from "../model/resolution/Annotation";
import {Person} from "../model/resolution/Person";
import TimeUtil from "./TimeUtil";

function clone<T>(obj: T): T {
  return JSON.parse(JSON.stringify(obj)) as T;
}

export default class XmlResolutionConverter {

  private static tagNames = ['noot', 'persoon', 'instelling', 'plaats', 'scheepsnaam', 'literatuur', 'bibliografie'];
  private static sourceRegex = new RegExp('.*\\/(resoluties_staten_generaal.*\\/.*)');

  public static convert(file: any): EsResolutionDocument[] {
    const xml: Document = XmlUtil.getXml(file);
    const metadata = this.createMetadata(file, xml);
    const attendants = this.createAttendants(xml);
    return this.createEsDocs(xml, metadata, attendants);
  }

  private static createEsDocs(xml: Document, metadata: Metadata, attendants: Person[]) {
    const xmlResolutions = xml.getElementsByTagName('resolutie');
    const esDocs: EsResolutionDocument[] = [];
    for (let i = 0; i < xmlResolutions.length; i++) {
      const m = clone<Metadata>(metadata);
      m.resolution = this.idxToResolution(i);
      const id = this.createId(xml, i);
      const result = this.createEsDoc(id, xmlResolutions[i], m, attendants);
      esDocs.push(result);
    }
    return esDocs;
  }

  private static createEsDoc(
    id: string,
    xmlResolution: Element,
    metadata: Metadata,
    attendants: Person[]
  ): EsResolutionDocument {
    const resolution = this.createResolution(xmlResolution);
    const annotations = this.createAnnotations(xmlResolution);
    const people = this.createPeople(attendants, annotations);
    return new EsResolutionDocument(id, metadata, people, resolution, annotations);
  }

  private static createAttendants(xml: Document): Person[] {
    if (0 === xml.getElementsByTagName('presentielijst').length) {
      return [];
    }

    const attendants: Person[] = [];

    const xmlAttendants = xml
      .getElementsByTagName('presentielijst')[0]
      .getElementsByTagName('prespersoon');

    for (let i = 0; i < xmlAttendants.length; i++) {
      const xmlAttendant = xmlAttendants[i];
      const id = parseInt(xmlAttendant.getElementsByTagName('persoon')[0].getAttribute('idnr').trim());
      const province = (xmlAttendant.parentNode as Element).getAttribute('naam');
      const name = xmlAttendant.textContent;
      let status = xmlAttendant.getAttribute('status');
      const president = status === 'president';
      const attendant = new Person(id, 'attendant', province, name, president);
      attendants.push(attendant);
    }
    return attendants;
  }

  private static createPeople(attendants: Person[], annotations: Annotation[]) {
    const people = JSON.parse(JSON.stringify(attendants)) as Person[];
    for (const ann of annotations) {
      if (ann.name == 'persoon') {
        const person = new Person(ann.id, 'mentioned', undefined, ann.value, false);
        people.push(person);
      }
    }
    return people;
  }

  private static createAnnotations(xmlResolution: Element): Annotation[] {
    const esAnns: Annotation[] = [];
    for (const tag of this.tagNames) {
      const xmlAnns: HTMLCollectionOf<Element> = xmlResolution.getElementsByTagName(tag)

      for (var i = 0; i < xmlAnns.length; i++) {
        const xmlAnn = xmlAnns[i];
        const id = parseInt(xmlAnn.getAttribute('idnr').trim());
        const esAnn = new Annotation(id ? id : undefined, tag, xmlAnn.textContent);
        esAnns.push(esAnn);
      }

    }
    return esAnns;
  }

  private static createResolution(xmlResolution: Element) {
    const parentNode = xmlResolution.parentNode;
    const postprandium = parentNode.nodeName === 'postprandium';
    const plainText = xmlResolution.textContent.trim();
    const originalXml = xmlResolution.toString();
    return new Resolution(postprandium, plainText, originalXml);
  }

  private static createMetadata(file: string, xml: Document): Metadata {
    const meetingDate = TimeUtil.getFormatted(this.createMeetingDate(xml));
    const meeting = new Meeting(meetingDate);
    const source = file.match(this.sourceRegex)[1];
    const indexedOn = TimeUtil.getNow();
    return new Metadata(meeting, source, indexedOn);
  }

  private static createMeetingDate(xml: Document): string {
    const year = xml.documentElement.getAttribute('jaar');
    const month = xml.documentElement.getAttribute('maand');
    const day = xml.documentElement.getAttribute('dag').trim();
    return `${year}-${month}-${day}`;
  }

  private static createId(xml: any, meetingResolutionIndex: number): string {
    return 'meeting-' + this.createMeetingDate(xml) + '-resolution-' + this.idxToResolution(meetingResolutionIndex);
  }

  private static idxToResolution(meetingResolutionIndex: number) {
    return meetingResolutionIndex + 1;
  }
}
