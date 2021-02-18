import EsError from "./EsError";
import {ERR_ES_NOT_AVAILABLE} from "../content/Placeholder";

export function handleEsError(e: Error, msg: string): never {
  console.trace('handle Es Error;', e);

  let resultMsg: string = '';

  if (
    e.message === 'No Living connections' ||
    e.message.includes('Request Timeout') ||
    e.message.includes('Bad Gateway')
  ) {
    resultMsg = ERR_ES_NOT_AVAILABLE;
  }

  const reason = resultMsg ? '\n Reden: ' + resultMsg : '';
  throw new EsError(`${msg}${reason}`, e);
}
