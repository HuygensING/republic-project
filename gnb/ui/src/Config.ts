
let env = process.env;

export default class Config {
  static ES_HOST: any;
  static ES_DATE: string;

  public static init() {
    this.ES_HOST = this.setEnvVar(env, 'REACT_APP_ES_HOST');
    this.ES_DATE = 'YYYY-MM-DD';
  }

  private static setEnvVar(env: any, key: string) : string {
    let value :string | undefined = env[key];
    if(!value) {
      throw Error(`environment variable ${key} is not set`);
    }
    return value;
  }

}

Config.init();
