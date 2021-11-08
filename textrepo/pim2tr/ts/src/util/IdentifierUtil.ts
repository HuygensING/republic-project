/**
 * Utility to handle external identifiers as used in Republic
 * - identifier:              NL-HaNA_{archief/toegang}_{inventarisnummer}
 * - as found in pim:         NL-HaNA_{series}_{set}_{scan}
 * - example externalId:      NL-HaNA_1.01.02_{4563}_{0062}
 */
import Config from "../Config";

export class ExternlIdParts {
  public archief: string;
  public inventaris: string;
  public scan: string;

  constructor(archief: string, inventaris: string, scan: string) {
    this.archief = archief;
    this.inventaris = inventaris;
    this.scan = scan;
  }
}

export default class IdentifierUtil {

  private static identifierFormat = new RegExp('NL-HaNA_([0-9.]*)_([0-9a-zA-Z]*)');
  private static externalIdentifierFormat = new RegExp('NL-HaNA_([0-9.]*)_([0-9a-zA-Z]*)_([0-9a-zA-Z-_]*)');
  private static scanFormat = new RegExp('NL-HaNA_[0-9\.]*_[0-9a-zA-Z]*_([0-9a-zA-Z-_]*)\.jpg');

  /**
   * Extract series and set ID from identifiers
   *
   * Example:
   * - identifier: NL-HaNA_1.10.94_0455
   * - series:     1.10.94
   * - set:        0455
   *
   * @return (string series, string set)
   */
  public static extractArchiefAndInventarisFrom(identifier: string) {
    const groups = identifier.match(this.identifierFormat);
    return [groups[1], groups[2]];
  }

  public static checkExternalId(identifier: string) {
    if (!this.externalIdentifierFormat.test(identifier)) {
      throw new Error(
        `Could not create externalId from ${identifier}: should conform to ${this.externalIdentifierFormat}`
      );
    }
  }

  /**
   * Pim set contains no leading zeros
   */
  public static inventaris2set(inventaris: string) {
    return inventaris.replace(/^0+/, '');
  }

  /**
   * Pim series is prefixed with NL-HaNA_
   */
  public static archief2series(archief: string) {
    return 'NL-HaNA_' + archief;
  }

  /**
   * Extract scan 'number' from remoteuri
   */
  public static remoteuri2scan(remoteuri) {
    const split = remoteuri.split('/');
    const img = split[split.length - 1]
    return img.match(this.scanFormat)[1];
  }

  public static createExternalId(identifier, scanNo) {
    const externalId = identifier + '_' + scanNo;
    this.checkExternalId(externalId);
    return externalId;
  }

  /**
   * Extract archief, inventaris and scan number from externalId
   */
  static externalId2Parts(docId: string): ExternlIdParts {
    const parts = docId.match(this.externalIdentifierFormat);
    return new ExternlIdParts(parts[1], parts[2], parts[3]);
  }

  /**
   * Find set in documentimagesets by archief- and inventarisnummer
   */
  static findSet(docImgSets: any, archief: string, inventaris: string) {
    const setNo = IdentifierUtil.inventaris2set(inventaris);
    const seriesNo = IdentifierUtil.archief2series(archief);
    const found = docImgSets.filter(set => {
      let groups = set.uri.match(/.*\/statengeneraal\/(.*)\/([0-9]{4})/);
      if (!groups) {
        return false;
      }
      const seriesGroup = groups[1];
      const setGroup = groups[2];
      const seriesMatch = seriesGroup === seriesNo;
      const setMatch = setGroup === setNo;
      return seriesMatch && setMatch;
    });
    if (found.length !== 1) {
      throw new Error(`Expected single set for ${seriesNo} and ${inventaris}, but got ${JSON.stringify(found)}`);
    }
    return found[0];
  }
}
