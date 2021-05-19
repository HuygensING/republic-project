import {memo, MutableRefObject} from "react";
import moment from "moment";
import 'moment/locale/nl'
import {DataEntry} from "../../common/plot/DataEntry";
import {useResolutionContext} from "../../resolution/ResolutionContext";
import {useAsyncError} from "../../hook/useAsyncError";
import {fromEsFormat} from "../../util/fromEsFormat";
import {useClientContext} from "../../elastic/ClientContext";
import Place from "../model/Place";
import {C5} from "../../style/Colors";
import {usePlotContext} from "../../common/plot/PlotContext";
import renderPlot from "../../common/plot/Plot";
import {equal} from "../../util/equal";
import {useLoadingContext} from "../../LoadingContext";
import {randStr} from "../../util/randStr";
import {usePrevious} from "../../hook/usePrevious";
import useSetLoadingWhen from "../../hook/useSetLoadingWhen";

moment.locale('nl');

type PlaceHistogramProps = {
  svgRef: MutableRefObject<any>,
  handleResolutions: (r: string[]) => void,
  place: Place,
  memoKey: any
}

/**
 * Bar chart rendered on svgRef
 */
export const PlacePlot = memo(function (props: PlaceHistogramProps) {

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

    const rIds = bars.reduce((all, arr: DataEntry) => all.concat(arr.ids), [] as string[]);
    client.resolutionResource.aggregateByPlace(
      rIds,
      props.place,
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
        {color: C5, y: {title: props.place.val}},
        props.handleResolutions
      );
      setLoadingState({event: eventName, loading: false});

    }).catch(throwError);
  }

  return null;

}, (prev, next) => equal(prev.memoKey, next.memoKey));
