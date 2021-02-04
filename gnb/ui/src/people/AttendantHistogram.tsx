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

moment.locale('nl');

type AttendantHistogramProps = {
  client: GnbElasticClient,
  svgRef: MutableRefObject<any>,
  handleResolutions: (r: string[]) => void
}

/**
 * Bar chart rendered on svgRef
 */
export default function AttendantHistogram(props: AttendantHistogramProps) {

  const {resolutionState} = useResolutionContext();
  const prevResolutions = usePrevious(resolutionState.resolutions);
  const resolutionStateChanged = !equal(prevResolutions, resolutionState.resolutions);

  // TODO: make configurable:
  const attendant = 360496;

  const throwError = useAsyncError();

  if(resolutionStateChanged) {
    updateHistogram();
  }

  function updateHistogram() {

    props.client.resolutionResource.aggregateByPerson(
      resolutionState.resolutions.reduce((all, arr: HistogramBar) => all.concat(arr.ids), [] as string[]),
      attendant,
      PersonType.ATTENDANT
    ).then((buckets: any) => {
      const bars = buckets.map((b: any) => ({
        date: b.key_as_string,
        count: b.doc_count,
        ids: b.resolution_ids.buckets.map((b: any) => b.key)
      } as HistogramBar));

      renderHistogram(
        props.svgRef,
        bars,
        props.handleResolutions
      );

    }).catch(throwError);

  }

  return null;

};

