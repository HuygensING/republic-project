import {MutableRefObject} from "react";
import moment from "moment";
import 'moment/locale/nl'
import {DataEntry} from "../../common/plot/DataEntry";
import {useResolutionContext} from "../../resolution/ResolutionContext";
import {useAsyncError} from "../../hook/useAsyncError";
import {fromEsFormat} from "../../util/fromEsFormat";
import {useClientContext} from "../../elastic/ClientContext";
import {Term} from "../model/Term";
import {C3} from "../../style/Colors";
import {usePlotContext} from "../../common/plot/PlotContext";
import renderPlot from "../../common/plot/Plot";
import {useLoadingContext} from "../../LoadingContext";
import {randStr} from "../../util/randStr";
import {usePrevious} from "../../hook/usePrevious";
import useSetLoadingWhen from "../../hook/useSetLoadingWhen";

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
export const TermPlot = function (props: TermHistogramProps) {

  const {resolutionState} = useResolutionContext();
  const throwError = useAsyncError();
  const client = useClientContext().clientState.client;
  const {plotState} = usePlotContext();
  const {setLoadingState} = useLoadingContext();
  const eventName = randStr();
  const memokeyChanged = usePrevious(props.memoKey) !== props.memoKey;

  if (memokeyChanged) updateHistogram();
  useSetLoadingWhen(eventName, true, memokeyChanged);

  function updateHistogram() {

    const bars = resolutionState.resolutions;
    if (!bars.length) {
      return;
    }

    client.resolutionResource.aggregateByTerm(
      bars.reduce((all: any, arr: DataEntry) => all.concat(arr.ids), [] as string[]),
      props.term,
      fromEsFormat(bars[0].date),
      fromEsFormat(bars[bars.length - 1].date)
    ).then((buckets: any) => {
      const data = buckets.map((b: any) => ({
        date: b.key_as_string,
        count: b.doc_count,
        ids: b.resolution_ids.buckets.map((b: any) => b.key)
      } as DataEntry));

      renderPlot(
        plotState.type,
        props.svgRef,
        data,
        {color: C3, y: {title: props.term.val}},
        props.handleResolutions
      );
      setLoadingState({event: eventName, loading: false});

    }).catch(throwError);
  }

  return null;

};
