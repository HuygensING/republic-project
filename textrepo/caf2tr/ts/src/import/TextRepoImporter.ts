import ImportResult from "./model/ImportResult";

export interface TextRepoImporter<T> {
  run(): Promise<ImportResult<T>>;
}
