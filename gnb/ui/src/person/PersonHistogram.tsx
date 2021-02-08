import {MutableRefObject} from "react";
import GnbElasticClient from "../elastic/GnbElasticClient";
import moment from "moment";
import 'moment/locale/nl'
import {HistogramBar, renderHistogram} from "../common/Histogram";
import {useResolutionContext} from "../resolution/ResolutionContext";
import {PersonType} from "../elastic/model/PersonType";
import {useAsyncError} from "../hook/useAsyncError";
import {fromEsFormat} from "../util/fromEsFormat";
import {Person, toName} from "../elastic/model/Person";

moment.locale('nl');

type AttendantHistogramProps = {
  client: GnbElasticClient,
  svgRef: MutableRefObject<any>,
  handleResolutions: (r: string[]) => void,
  person: Person
  type: PersonType,
}

/**
 * Bar chart rendered on svgRef
 */
export default function PersonHistogram(props: AttendantHistogramProps) {

  const {resolutionState} = useResolutionContext();
  const throwError = useAsyncError();

  updateHistogram();

  function updateHistogram() {
    const bars = resolutionState.resolutions;

    if (!bars.length) {
      return;
    }

    props.client.resolutionResource.aggregateByPerson(
      bars.reduce((all, arr: HistogramBar) => all.concat(arr.ids), [] as string[]),
      props.person.id,
      props.type,
      fromEsFormat(bars[0].date),
      fromEsFormat(bars[bars.length - 1].date)
    ).then((buckets: any) => {
      const bars = buckets.map((b: any) => ({
        date: b.key_as_string,
        count: b.doc_count,
        ids: b.resolution_ids.buckets.map((b: any) => b.key)
      } as HistogramBar));

      renderHistogram(
        props.svgRef,
        bars,
        {bar: {color: "orange"}, y: {title: `With ${props.type} ${toName(props.person)}`}},
        props.handleResolutions
      );

    }).catch(throwError);

  }

  return null;

};
