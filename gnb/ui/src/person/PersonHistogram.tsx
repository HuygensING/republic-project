import {MutableRefObject} from "react";
import GnbElasticClient from "../elastic/GnbElasticClient";
import moment from "moment";
import 'moment/locale/nl'
import {HistogramBar, renderHistogram} from "../common/Histogram";
import {usePrevious} from "../hook/usePrevious";
import {equal} from "../util/equal";
import {useResolutionContext} from "../resolution/ResolutionContext";
import {PersonType} from "../elastic/model/PersonType";
import {useAsyncError} from "../hook/useAsyncError";
import {fromEsFormat} from "../util/fromEsFormat";
import {usePersonContext} from "./PersonContext";
import {toName} from "../elastic/model/Person";

moment.locale('nl');

type AttendantHistogramProps = {
  client: GnbElasticClient,
  svgRef: MutableRefObject<any>,
  handleResolutions: (r: string[]) => void
}

/**
 * Bar chart rendered on svgRef
 */
export default function PersonHistogram(props: AttendantHistogramProps) {

  const {resolutionState} = useResolutionContext();
  const prevResolutions = usePrevious(resolutionState.resolutions);
  const resolutionStateChanged = !equal(prevResolutions, resolutionState.resolutions);

  const {personState} = usePersonContext();
  // const prevPerson = usePrevious(personState.person);
  // const personStateChanged = !equal(prevPerson, personState.person);

  const throwError = useAsyncError();

  if(resolutionStateChanged) {
    // TODO:
    //  - pick person: how?
    //  - retrieve person data and set as personState
    //  - updateHistogram
    updateHistogram();
  }

  function updateHistogram() {
    const bars = resolutionState.resolutions;

    if(!bars.length) {
      return;
    }

    props.client.resolutionResource.aggregateByPerson(
      bars.reduce((all, arr: HistogramBar) => all.concat(arr.ids), [] as string[]),
      personState.person.id,
      PersonType.ATTENDANT,
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
        {bar: {color: "orange"}, y: {title: `With ${personState.type} ${toName(personState.person)}`}},
        props.handleResolutions
      );

    }).catch(throwError);

  }

  return null;

};
