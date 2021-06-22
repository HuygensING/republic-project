import DocumentImagesResource from "./DocumentImagesResource";
import {DocumentImageSetResource} from "./DocumentImageSetResource";
import DocumentImageTranscriptionsResource from "./DocumentImageTranscriptionsResource";
import {DocumentImageTranscriptionsResourceImpl} from "./DocumentImageTranscriptionsResourceImpl";
import DocumentImageSetResourceImpl from "./DocumentImageSetResourceImpl";

/**
 * Client for Pergamon Images
 */
export default class PimClient {
    private host: string;
    private authorization: string;

    private _documentImageSet: DocumentImageSetResource;
    private _documentImages: DocumentImagesResource;
    private _documentImageTranscriptions: DocumentImageTranscriptionsResource;

    constructor(host: string, authorization: string) {
        this.authorization = authorization;
        this.host = host + '/api/pim';

        this._documentImageSet = new DocumentImageSetResourceImpl(this.host, this.authorization);
        this._documentImages = new DocumentImagesResource(this.host, this.authorization);
        this._documentImageTranscriptions = new DocumentImageTranscriptionsResourceImpl(this.host, this.authorization);
    }

    get documentImageSet(): DocumentImageSetResource {
        return this._documentImageSet;
    }

    get documentImages(): DocumentImagesResource {
        return this._documentImages;
    }

    get documentImageTranscriptions(): DocumentImageTranscriptionsResource {
        return this._documentImageTranscriptions;
    }

}
