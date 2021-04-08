import TypesResource from "./resource/TypesResource";
import DocumentMetadataResource from "./resource/DocumentMetadataResource";
import VersionMetadataResource from "./resource/VersionMetadataResource";
import TasksResource from "./resource/TasksResource";
import DocumentsResource from "./resource/DocumentsResource";
import DocumentFilesResource from "./resource/DocumentFilesResource";
import FilesResource from "./resource/FilesResource";

/**
 * Client for Text Repository
 */
export default class TextRepoClient {
  private restHost: string;

  private _documentMetadata: DocumentMetadataResource;
  private _types: TypesResource;
  private _versionMetadata: VersionMetadataResource;
  private taskHost: string;
  private _tasks: TasksResource;
  private _documents: DocumentsResource;
  private _documentFiles: DocumentFilesResource;
  private _files: FilesResource;

  constructor(host: string) {
    this.restHost = host + '/rest';
    this.taskHost = host + '/task'
    this._documentMetadata = new DocumentMetadataResource(this.restHost);
    this._types = new TypesResource(this.restHost);
    this._versionMetadata = new VersionMetadataResource(this.restHost);
    this._tasks = new TasksResource(this.taskHost);
    this._documents = new DocumentsResource(this.restHost);
    this._documentFiles = new DocumentFilesResource(this.restHost);
    this._files = new FilesResource(this.restHost);
  }

  get documentMetadata(): DocumentMetadataResource {
    return this._documentMetadata;
  }

  get types(): TypesResource {
    return this._types;
  }

  get versionMetadata(): VersionMetadataResource {
    return this._versionMetadata;
  }

  get tasks(): TasksResource {
    return this._tasks;
  }

  get files(): FilesResource {
    return this._files;
  }
  get documentFiles(): DocumentFilesResource {
    return this._documentFiles;
  }
  get documents(): DocumentsResource {
    return this._documents;
  }
}
