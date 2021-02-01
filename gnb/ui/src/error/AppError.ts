/**
 * Custom Error class
 * See: https://www.typescriptlang.org/docs/handbook/release-notes/typescript-2-2.html#support-for-newtarget
 */
export default class AppError extends Error {
  private original: Error;
  constructor(message: string, original: Error) {
    super(message);
    Object.setPrototypeOf(this, new.target.prototype);
    this.original = original;
  }
}
