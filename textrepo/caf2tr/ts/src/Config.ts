import * as process from "process";

let env = process.env;

export default class Config {
    static TMP;
    static TR;
    static CACHE;

    public static init() {
        this.TMP = env.TMP;
        this.TR = env.TR;
        this.CACHE = env.CACHE;

        for (var prop in this) {
            if (Object.prototype.hasOwnProperty.call(this, prop)) {
                if(this[prop] === undefined) {
                    throw new Error(`Environment variable ${prop} was undefined.`);
                }
            }
        }
    }
}

Config.init();
