export default class StringUtil {

  private static toStrip = /[\t\n\r ]+/g;

  /**
   * Trim and remove excess tabs, newlines and double spaces
   */
  public static clean(strippable: string) : string {
    return strippable
      .replace(this.toStrip, ' ')
      .trim();
  }
}
