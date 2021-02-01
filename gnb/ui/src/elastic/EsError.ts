/**
 * Custom Error class
 * See: https://www.typescriptlang.org/docs/handbook/release-notes/typescript-2-2.html#support-for-newtarget
 */
import AppError from "../error/AppError";

export default class EsError extends AppError {
  constructor(message: string, original: Error) {
    super(message, original);
    Object.setPrototypeOf(this, new.target.prototype);
  }
}
