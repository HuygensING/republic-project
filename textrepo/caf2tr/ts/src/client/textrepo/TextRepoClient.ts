import TypesResource from "./resource/TypesResource";
import TasksResource from "./resource/TasksResource";

/**
 * Client for Text Repository
 */
export default class TextRepoClient {
  private restHost: string;
  private taskHost: string;

  private _types: TypesResource;
  private _tasks: TasksResource;

  constructor(host: string) {
    this.restHost = host + '/rest';
    this.taskHost = host + '/task'
    this._types = new TypesResource(this.restHost);
    this._tasks = new TasksResource(this.taskHost);
  }

  get types(): TypesResource {
    return this._types;
  }

  get tasks(): TasksResource {
    return this._tasks;
  }

}
