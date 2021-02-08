import {fromEsFormat} from "./fromEsFormat";

export function id2date(resolutionId: string): Date {
  return fromEsFormat(resolutionId.slice(8,18));
}
