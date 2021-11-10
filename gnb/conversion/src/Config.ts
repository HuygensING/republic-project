import * as process from "process";

let env = process.env;

export default class Config {
    static XML_GLOB;
    static ES_VERSION;
    static ES_HOST;
    static MYSQL_CONNECTION;
    static RESOLUTION_INDEX;
    static PERSON_INDEX;
    static DATE_FORMAT;

    public static init() {
        this.XML_GLOB = env.XML_GLOB;
        this.ES_VERSION = env.ES_VERSION;
        this.ES_HOST = env.ES_HOST;
        this.MYSQL_CONNECTION = env.MYSQL_CONNECTION;
        this.RESOLUTION_INDEX = env.RESOLUTION_INDEX;
        this.PERSON_INDEX = env.PERSON_INDEX;
        this.DATE_FORMAT = env.DATE_FORMAT;

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
