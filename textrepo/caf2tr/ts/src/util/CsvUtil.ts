import Config from "../Config";
import CsvReader from "./CsvReader";

/**
 * Utility to handle external identifiers as used in Republic
 * - identifier:              NL-HaNA_{archief/toegang}_{inventarisnummer}
 * - as found in pim:         NL-HaNA_{series}_{set}_{scan}
 * - example externalId:      NL-HaNA_1.01.02_{4563}_{0062}
 */
export default class CsvUtil {

    public static async getRecords<T>(csvPath: string): Promise<T[]> {
        let records = await new CsvReader(csvPath).read();
        return records.filter(r => !!r);
    }

}
