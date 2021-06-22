import ImportResult from "./model/ImportResult";
import {TextRepoModel} from "../client/textrepo/model/TextRepoModel";
import {DocumentResult} from "./model/DocumentResult";
import TextRepoDocument from "../client/textrepo/model/TextRepoDocument";

export interface TextRepoImporter<T extends TextRepoModel> {
  run(): Promise<ImportResult<T>>;
}
