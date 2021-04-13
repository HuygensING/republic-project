import RestUtil from "../RestUtil";
import DocumentImageTranscriptionsResource from "./DocumentImageTranscriptionsResource";

export class DocumentImageTranscriptionsResourceDummy implements DocumentImageTranscriptionsResource {

    // 1 mb
    private someResult = '1'.repeat(1024 * 1024);

    private transcribers = ['Tesseract4', 'CustomTesseractPageXML', 'Transkribus']

    private transcription = {
        "format": null,
        "id": 9884176,
        "documentImageId": 63384781,
        "result": this.someResult,
        "transcriber": "CustomTesseractPageXML",
        "version": "0.01",
        "analyzed": 1583233072030,
        "params": null,
        "uuid": null,
        "cleanText": null,
        "language": null,
        "status": null
    }

    // Source: https://stackoverflow.com/questions/58325771/how-to-generate-random-hex-string-in-javascript
    private randomHex = size => [...Array(size)].map(() => Math.floor(Math.random() * 16).toString(16)).join('');

    private randomTranscription = size => [...Array(size)].map(() => {
        const t = this.transcription;
        t.uuid = '4f753c39-7c34-401d-b029-' + this.randomHex(12);
        t.transcriber = this.transcribers[Math.floor(Math.random() * this.transcribers.length)];
        return t;
    });

    /**
     * Returns 3 transcription with:
     * - random uuids,
     * - random transcribers
     * - and a result containing some large string of 1's
     */
    async getAll(imageI: string): Promise<any> {
        console.log('getAll dummy transcriptions');
        await RestUtil.wait(50);
        return Promise.resolve(this.randomTranscription(2));
    }
}
