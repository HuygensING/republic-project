export class Resolution {
  public postprandium: boolean;
  public plainText: string;
  public originalXml: string;

  constructor(postprandium: boolean, plainText: string, originalXml: string) {
    this.postprandium = postprandium;
    this.plainText = plainText;
    this.originalXml = originalXml;
  }
}
