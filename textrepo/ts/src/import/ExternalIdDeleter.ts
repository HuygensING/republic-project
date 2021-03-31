import {TextRepoImporter} from "./TextRepoImporter";
import TextRepoClient from "../client/textrepo/TextRepoClient";
import IdUtil from "../util/IdentifierUtil";
import IdentifierUtil from "../util/IdentifierUtil";
import PimClient from "../client/pim/PimClient";
import ImportResult from "./model/ImportResult";
import CsvIdentifierRecord from "./model/CsvIdentifierRecord";
import ErrorHandler from "../client/ErrorHandler";
import {DocumentResult} from "./model/DocumentResult";

/**
 * Delete a document by its externalId, including all its files, contents and metadata
 */
export default class ExternalIdDeleter implements TextRepoImporter<string> {

    private textRepoClient: TextRepoClient;
    private pimClient: PimClient;

    private records: CsvIdentifierRecord[];

    constructor(textRepoClient: TextRepoClient, pimClient: PimClient, records: CsvIdentifierRecord[]) {
        this.textRepoClient = textRepoClient;
        this.pimClient = pimClient;
        this.records = records;
    }

    public async run(): Promise<ImportResult<string>> {
        console.log(`Deleting documents for ${this.records.length} csv records`);
        const documentImageSet = await this.pimClient.documentImageSet.getAll();
        const newDocs: string[] = [];
        let success = true;
        for (const record of this.records) {

            const identifier = record.identifier;
            const [archiefNo, inventarisNo] = IdUtil.extractArchiefAndInventarisFrom(identifier);
            const set = IdentifierUtil.findSet(documentImageSet, archiefNo, inventarisNo);
            const documentImages = await this.pimClient.documentImages.getAll(set.uuid);

            console.log(`Deleting ${documentImages.length} documents for inventaris ${identifier}`)
            for (const img of documentImages) {
                try {
                    const deleted = await this.deleteDocument(img, identifier);
                    if (deleted.isSuccesful()) {
                        newDocs.push(...deleted.results);
                    } else {
                        success = false;
                    }
                } catch (e) {
                    success = false;
                    ErrorHandler.handle(`Could not delete document ${identifier} for img ${img.remoteuri}`, e);
                }
            }
        }

        return new ImportResult<string>(true, newDocs);
    }

    /**
     * Create document, or get existing document when externalId already used
     */
    private async deleteDocument(img, identifier): Promise<ImportResult<string>> {
        const scanNo = IdUtil.remoteuri2scan(img.remoteuri);
        const externalId = IdUtil.createExternalId(identifier, scanNo);
        const doc = await this.textRepoClient.documents.getByExternalId(externalId);
        if(!doc) {
            let result = `No document found for ${externalId}`;
            console.log(result);
            return new ImportResult<string>(false, [result])
        } else {
            console.log(`Deleted document ${doc.id}`);
        }
        const files = await this.textRepoClient.documentFiles.getAll(doc.id);

        let deletedAllFiles = true;
        for (const f of files) {
            const deleted = await this.textRepoClient.files.delete(f.id);

            if (deleted) {
                console.log(`Deleted file ${f.id}`);
            } else {
                deletedAllFiles = false;
            }
        }

        if (!deletedAllFiles) {
            ErrorHandler.print(`Could not delete all files by externalId ${externalId}`);
            return new ImportResult<string>(false, [externalId]);
        }

        let deletedDoc = await this.textRepoClient.documents.delete(doc.id);

        if (!deletedDoc) {
            ErrorHandler.print(`Could not delete document by its ${externalId}`);
        }
        console.log(`Deleted document: ${doc.id}`);

        const success = deletedAllFiles && deletedDoc;
        return new ImportResult<string>(success, [doc.id]);
    }


}
