import {TextRepoImporter} from "./TextRepoImporter";
import ImportResult from "./model/ImportResult";
import TextRepoClient from "../client/textrepo/TextRepoClient";
import PimClient from "../client/pim/PimClient";
import CsvIdentifierRecord from "./model/CsvIdentifierRecord";
import {DocumentResult} from "./model/DocumentResult";
import IdUtil from "../util/IdentifierUtil";
import IdentifierUtil, {ExternlIdParts} from "../util/IdentifierUtil";
import ErrorHandler from "../client/ErrorHandler";
import TextRepoDocument from "../client/textrepo/model/TextRepoDocument";
import TmpUtil from "../util/TmpUtil";
import TextRepoType from "../client/textrepo/model/TextRepoType";
import {ImportEndpointResult} from "./model/ImportEndpointResult";

const KEY_PREFIX = 'pim:image:';
export const IMAGE_UUID_KEY = KEY_PREFIX + 'uuid';

/**
 * Import using <textrepo>/task/import
 */
export default class TaskImportImporter {

  private textRepoClient: TextRepoClient;
  private pimClient: PimClient;
  private records: CsvIdentifierRecord[];

  private pimImageMetadataFields = [
    {pimKey: 'uuid', trKey: IMAGE_UUID_KEY},
    {pimKey: 'remoteuri', trKey: KEY_PREFIX + 'remoteuri'},
    {pimKey: 'tesseract4BestHOCRVersion', trKey: KEY_PREFIX + 'tesseract4besthocrversion'},
    {pimKey: 'tesseract4BestHOCRAnalyzed', trKey: KEY_PREFIX + 'tesseract4BestHOCRAnalyzed'}
  ];

  private relevantTranscribers = [
    {'transcriber': 'CustomTesseractPageXML', 'type': 'pagexml'},
    {'transcriber': 'Tesseract4', 'type': 'hocr'},
    {'transcriber': 'Transkribus', 'type': 'pagexml'}
  ];

  private relevantTranskribusStatuses = [
    'GT', 'Final', 'IN_PROGRESS'
  ];

  private prefix = 'pim:transcription:';
  private pimTranscriptionMetadataFields = [
    {pimKey: 'uuid', trKey: this.prefix + 'uuid'},
    {pimKey: 'transcriber', trKey: this.prefix + 'transcriber'},
    {pimKey: 'version', trKey: this.prefix + 'version'},
    {pimKey: 'analyzed', trKey: this.prefix + 'analyzed'}
  ];

  private types: TextRepoType[];

  private versionCounter = 0;

  constructor(
    textRepoClient: TextRepoClient,
    pimClient: PimClient,
    records: CsvIdentifierRecord[],
    types: TextRepoType[]
  ) {
    this.textRepoClient = textRepoClient;
    this.pimClient = pimClient;
    this.records = records;
    this.types = types;
  }

  async run(test?: boolean): Promise<number> {
    console.log(`Create documents for ${this.records.length} csv records`);
    const documentImageSet = await this.pimClient.documentImageSet.getAll();
    let success = true;

    for (const record of this.records) {

      const identifier = record.identifier;
      const [archiefNo, inventarisNo] = IdUtil.extractArchiefAndInventarisFrom(identifier);
      const set = IdentifierUtil.findSet(documentImageSet, archiefNo, inventarisNo);

      let documentImages = await this.pimClient.documentImages.getAll(set.uuid);

      if (test) {
        documentImages = documentImages.slice(0, 1);
      }

      let counter = 0;
      for (const img of documentImages) {

        console.log(`Handling img ${++counter} of ${documentImages.length}: ${img.uuid}`);

        const scanNo = IdUtil.remoteuri2scan(img.remoteuri);
        const externalId = IdentifierUtil.createExternalId(identifier, scanNo);

        let allPimVersions = await this.getAndCachePimVersions(img.uuid);
        allPimVersions.sort((a, b) => a.analyzed - b.analyzed);

        let docMetadataCreated = false;

        for (const type of this.types) {
          const pimVersionsToAdd: any[] = this.findRelevantVersions(allPimVersions, type.id);

          for (const i in pimVersionsToAdd) {
            const pv = pimVersionsToAdd[i];
            if (pv.result == null) {
              console.log(`WARN Version contents is ${pv.result}: set to ''`);
              pv.result = '';
            }

            try {

              let isLatestVersion = parseInt(i) === (pimVersionsToAdd.length - 1);

              console.log(`Importing externalId ${externalId} and type ${type.id}  (analyzed: ${pv.analyzed})`);
              const result = await this.textRepoClient.tasks.import(
                  type.name,
                externalId,
                pv.result,
                isLatestVersion
              );

              const {documentId, fileId, versionId, newVersion} = result;

              if (newVersion) {
                console.log(`Created version ${versionId} with document ${documentId} and file ${fileId}`);
                this.versionCounter++;
              } else {
                console.log('Version already existed for versionId', versionId);
              }

              if (!docMetadataCreated) {
                console.log('Creating metadata for document', documentId);
                await this.createDocumentMetadata({id: documentId, externalId} as DocumentResult, img);
                docMetadataCreated = true;
              }

              if (newVersion) {
                console.log('Creating metadata for version', versionId);
                await this.createVersionPimMetadata(pv, versionId);
              }

            } catch (e) {
              success = false;
              ErrorHandler.handle(`Could not import pim transcription ${pv.uuid} of scan ${img.uuid}`, e);
            }
          }
        }
      }
    }
    return this.versionCounter;
  }

  private async createExternalIdMetadata(parts: ExternlIdParts, newDoc: TextRepoDocument) {
    const metadata = {};
    Object.keys(parts).forEach(k => {
      this.textRepoClient.documentMetadata.create(newDoc.id, k, parts[k]);
      metadata[k] = parts[k];
    });
    return metadata;
  }

  /**
   * Store pim transcriptions in cache
   * to prevent downloading all transcriptions multiple times
   * for each file type
   */
  private async getAndCachePimVersions(pimImageUuid: string): Promise<any[]> {
    let cache: string = await TmpUtil.getCache(pimImageUuid);
    if (cache) {
      return await JSON.parse(cache);
    }
    let uncached = await this.pimClient.documentImageTranscriptions.getAll(pimImageUuid);
    await TmpUtil.setCache(pimImageUuid, JSON.stringify(uncached));
    return uncached;
  }

  private findRelevantVersions(pimVersions, typeId: number) {
    return pimVersions.filter(pv => {
      let relevantTranscriberNamesByType = this.relevantTranscribers
        .filter(rt => rt.type === this.findTypeBy(typeId).name)
        .map(rt => rt.transcriber);

      const relevantVersion = relevantTranscriberNamesByType
        .includes(pv.transcriber)

      if (pv.transcriber === 'Transkribus') {
        const relevantStatus = this.relevantTranskribusStatuses.includes(pv.status);
        return relevantVersion && relevantStatus;
      } else {
        return relevantVersion;
      }
    });
  }

  private findTypeBy(typeId: number) {
    let result = this.types.find(t => t.id === typeId);
    if (!result) {
      throw new Error(`Could not find type by id ${typeId} in ${JSON.stringify(this.types)}`);
    }
    return result;
  }

  private async createVersionPimMetadata(pimMetadata: object, newVersion: string) {
    const metadata = {};
    this.pimTranscriptionMetadataFields.forEach(f => {
      this.textRepoClient.versionMetadata.create(newVersion, f.trKey, pimMetadata[f.pimKey]);
      metadata[f.trKey] = pimMetadata[f.pimKey];
    });
    return metadata;
  }

  private async createDocumentMetadata(newDoc: DocumentResult, img) {
    const parts = IdUtil.externalId2Parts(newDoc.externalId);
    newDoc.metadata = {
      ...await this.createPimMetadata(img, newDoc),
      ...await this.createExternalIdMetadata(parts, newDoc)
    };
  }

  private async createPimMetadata(pimMetadata: object, newDoc: TextRepoDocument) {
    const metadata = {};
    this.pimImageMetadataFields.forEach(f => {
      this.textRepoClient.documentMetadata.create(newDoc.id, f.trKey, pimMetadata[f.pimKey]);
      metadata[f.trKey] = pimMetadata[f.pimKey];
    });
    return metadata;
  }

}
