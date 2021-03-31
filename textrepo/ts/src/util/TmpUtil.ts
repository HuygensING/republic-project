import Config from "../Config";
import * as flatCache from 'flat-cache';
import * as path from "path";

const MAX_CACHE_KEYS = 500;

export default class TmpUtil {

    private static cache = TmpUtil.createCache('tmp');

    private static tmpFile = TmpUtil.createCache('tmpFile');

    public static async setCache(key: string, value: string) {
        if (this.cache.keys().length > MAX_CACHE_KEYS) {
            await this.deleteCache();
        }
        return this.cache.setKey(key, value);
    }

    /**
     * Return contents of cache, or null when nothing cached
     */
    public static async getCache(key) {
        return await this.cache.getKey(key);
    }

    public static async deleteCache() {
        console.log('Delete cache');
        this.cache.destroy();
    }

    public static async storeToTmpFile(content: any, key: string) {
        this.tmpFile.setKey(key, content);
        this.tmpFile.save();
    }

    public static async getFromTmpFile(key: string): Promise<any> {
        return await this.tmpFile.getKey(key);
    }

    static createTmpKey(prefix: string) {
        return prefix
            + Config.SUBSET_CSV
                .replace('/', '')
                .replace(/\./g, '')
            + '.json';
    }

    private static createCache(name: string) {
        return flatCache.load(name, path.resolve(Config.TMP));
    }


}
