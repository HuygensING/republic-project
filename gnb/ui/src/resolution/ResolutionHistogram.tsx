import {MutableRefObject} from "react";
import {useSearchContext} from "../search/SearchContext";
import GnbElasticClient from "../elastic/GnbElasticClient";
import moment from "moment";
import 'moment/locale/nl'
import {useAsyncError} from "../hook/useAsyncError";
import {HistogramBar, renderHistogram} from "../common/Histogram";
import {usePrevious} from "../hook/usePrevious";
import {equal} from "../util/equal";

moment.locale('nl');

type BarChartProps = {
  client: GnbElasticClient,
  svgRef: MutableRefObject<any>,
  handleResolutions: (r: string[]) => void
}

/**
 * Bar chart rendered on svgRef
 */
export default function ResolutionHistogram(props: BarChartProps) {

  const state = useSearchContext().state;
  const prevAttendants = usePrevious(state.attendants)
  const prevMentioned = usePrevious(state.mentioned)
  const prevStart = usePrevious(state.start)
  const prevFullText = usePrevious(state.fullText)

  const stateChanged =
    !equal(prevAttendants, state.attendants) ||
    !equal(prevMentioned, state.mentioned) ||
    !equal(prevStart, state.start) ||
    !equal(prevFullText, state.fullText);

  const throwError = useAsyncError();

  if (stateChanged) {
    createChart();
  }

  function createChart() {

    const attendants = state.attendants.map(p => p.id);
    const mentioned = state.mentioned.map(p => p.id);

    props.client.resolutionResource.aggregateBy(
      attendants,
      mentioned,
      state.start,
      state.end,
      state.fullText
    ).then(renderResolutionHistogram)
      .catch(throwError);

    function renderResolutionHistogram(buckets: any) {

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

    }
  }

  return null;

};

