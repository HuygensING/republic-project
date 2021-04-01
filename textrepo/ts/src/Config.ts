import * as process from "process";

let env = process.env;

export default class Config {
    static PIM;
    static GOOGLE_AUTHORIZATION;
    static SUBSET_CSV;
    static TMP;
    static TYPE_CSV;
    static TR;
    static CACHE;

    public static init() {
        this.PIM = env.PIM;
        this.GOOGLE_AUTHORIZATION = env.GOOGLE_AUTHORIZATION;
        this.SUBSET_CSV = env.SUBSET_CSV;
        this.TMP = env.TMP;
        this.TYPE_CSV = env.TYPE_CSV;
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
