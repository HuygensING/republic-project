import * as fs from "fs";
import * as xmldom from "xmldom"

export default class XmlUtil {
  public static getXml(path: string) : Document {
    const fileContents = fs.readFileSync(path, 'utf8');
    return new xmldom.DOMParser().parseFromString(fileContents);
  }
}
