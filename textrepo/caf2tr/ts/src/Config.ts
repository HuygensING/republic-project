import * as process from "process";

let env = process.env;

export default class Config {
    static TMP = '';
    static TR = '';
    static CACHE = '';
    static CAF = '';
    static CAF_INDEX = '';
}

for (const prop in Config) {
    if (!Config.hasOwnProperty(prop)) {
        continue;
    }
    if (env[prop] === undefined) {
        throw new Error(`Environment variable ${prop} was undefined.`);
    }
    Config[prop] = env[prop];
}
