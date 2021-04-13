let env = process.env;

export default class Config {
  static TAG: string;
  static COMMIT: string;
  static ES_HOST: any;
  static ES_DATE: string;

  public static init() {
    this.TAG = this.setEnvVar(env, 'REACT_APP_TAG');
    this.COMMIT = this.setEnvVar(env, 'REACT_APP_COMMIT');
    this.ES_HOST = this.setEnvVar(env, 'REACT_APP_ES_HOST');
    this.ES_DATE = this.setEnvVar(env, 'REACT_APP_ES_DATE');
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
