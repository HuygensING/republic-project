import {Response} from "node-fetch";

export default class ErrorHandler {

  private static errorPrefix = 'ERROR';
  private static newLine = ":\n";

  public static print(msg: string) {
    console.trace(this.errorPrefix, msg);
  }

  public static handle(msg: string, e: Error) {
    console.trace(this.errorPrefix, msg + this.newLine, e);
  }

}
