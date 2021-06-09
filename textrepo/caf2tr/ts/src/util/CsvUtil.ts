import CsvReader from "./CsvReader";

export default class CsvUtil {

    public static async getRecords<T>(csvPath: string): Promise<T[]> {
        let records = await new CsvReader(csvPath).read();
        return records.filter(r => !!r);
    }

}
