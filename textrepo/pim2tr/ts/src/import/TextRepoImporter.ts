import ImportResult from "./model/ImportResult";
import {TextRepoModel} from "../client/textrepo/model/TextRepoModel";

export interface TextRepoImporter<T extends TextRepoModel> {
  run(): Promise<ImportResult<T>>;
}
