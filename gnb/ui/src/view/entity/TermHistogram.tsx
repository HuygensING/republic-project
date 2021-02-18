import {memo, MutableRefObject} from "react";
import moment from "moment";
import 'moment/locale/nl'
import {HistogramBar, renderHistogram} from "../../common/Histogram";
import {useResolutionContext} from "../../resolution/ResolutionContext";
import {useAsyncError} from "../../hook/useAsyncError";
import {fromEsFormat} from "../../util/fromEsFormat";
import {useClientContext} from "../../elastic/ClientContext";
import {equal} from "../../util/equal";
import {PERSON_HISTOGRAM_PREFIX} from "../../content/Placeholder";
import {Term} from "../model/Term";
import {PERSIAN_GREEN} from "../../style/Colors";

moment.locale('nl');

type TermHistogramProps = {
  svgRef: MutableRefObject<any>,
  handleResolutions: (r: string[]) => void,
  term: Term,
  memoKey: any
}

/**
 * Bar chart rendered on svgRef
 */
export const TermHistogram = memo(function (props: TermHistogramProps) {

  const {resolutionState} = useResolutionContext();
  const throwError = useAsyncError();
  const client = useClientContext().clientState.client;

  updateHistogram();

  function updateHistogram() {

    const bars = resolutionState.resolutions;

    if (!bars.length) {
      return;
    }

    client.resolutionResource.aggregateByTerm(
      bars.reduce((all, arr: HistogramBar) => all.concat(arr.ids), [] as string[]),
      props.term,
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
        { color: PERSIAN_GREEN, y: { title: `${PERSON_HISTOGRAM_PREFIX} ${props.term.val}`}},
        props.handleResolutions
      );

    }).catch(throwError);
  }

  return null;

}, (prev, next) => equal(prev.memoKey, next.memoKey));
