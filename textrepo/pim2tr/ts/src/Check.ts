import fetch from "node-fetch";
import Config from "./Config";

class Check {

  private commands: string[];

  constructor() {
    this.commands = process.argv.slice(2);
  }

  public run() {
    console.log('Start check');
    switch (this.commands[0]) {
      case "external-id-type": {
        if (!this.commands[1] || !this.commands[2]) {
          console.error("run as:\ncheck external-id-type <external-id> <type-name>");
          break;
        }
        return this.checkByExternalIdAndType(this.commands[1], this.commands[2]);
      }
      default: {
        console.error("Could not run check. Expected check-name, but got:", this.commands)
        console.error("run as:\ncheck <check-name> [arguments]");
        break;
      }
    }

  }


  private async checkByExternalIdAndType(externalId: string, typeName: string) {

    console.log(`Check external ID ${externalId} and type ${typeName}`);

    let tr = Config.TR;
    let docId = (await (await fetch(
      tr + '/rest/documents?externalId=' + externalId
    )).json())
      .items[0].id;
    console.log('docId:', docId);

    const typeId = (await (await fetch(tr + '/rest/types'
    )).json())
      .find((t: any) => t.name === typeName).id;
    console.log('typeId:', typeId);

    const fileId = (await (await fetch(
      tr + `/rest/documents/${docId}/files`
    )).json())
      .items
      .find((f: any) => f.typeId === typeId)
      .id;
    console.log('fileId:', fileId);

    const latestVersion = (await (await fetch(
      tr + `/rest/files/${fileId}/versions`))
      .json())
      .items[0];

    const latestVersionId = latestVersion.id;
    console.log('latestVersionId:', latestVersionId);

    const latestContentsSha = latestVersion.contentsSha;
    console.log('latestContentsSha:', latestContentsSha);

    const imageUuid = (await (await fetch(
      tr + `/rest/documents/${docId}/metadata`)).json())
      ['pim:image:uuid'];
    console.log('imageUuid:', imageUuid);

    const transcriptionUuid = (await (await fetch(
      tr + `/rest/versions/${latestVersionId}/metadata`
    )).json())
      ['pim:transcription:uuid'];
    console.log('transcriptionUuid:', transcriptionUuid);

    let versionContentsUrl = tr + `/rest/contents/${latestContentsSha}`;
    console.log(`latest version contents url: ${versionContentsUrl}`);
    const versionContents = (await (await fetch(
      versionContentsUrl
    )).text());
    console.log(`latest version contents substring:\n${versionContents.substr(0, 200)}[..]`);

    let transcriptionUrl = Config.PIM + `/api/pim/documentimage/${imageUuid}/transcriptions`;
    console.log(`transcription url ${transcriptionUrl}`);
    const imageTranscriptions: any[] = (await (await fetch(
      transcriptionUrl,
      {headers: {'authorization': Config.GOOGLE_AUTHORIZATION}}
    )).json());
    const transcriptionContents = imageTranscriptions
      .find((it: any) => it.uuid === transcriptionUuid)
      .result;
    console.log(`transcription substring:\n${transcriptionContents.substr(0, 200)}[..]`);

    let match = transcriptionContents === versionContents;
    console.log('contents match?', match);
  }
}

new Check().run();
