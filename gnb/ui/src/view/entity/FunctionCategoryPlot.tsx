import {MutableRefObject} from "react";
import moment from "moment";
import 'moment/locale/nl'
import {DataEntry} from "../../common/plot/DataEntry";
import {useResolutionContext} from "../../resolution/ResolutionContext";
import {useAsyncError} from "../../hook/useAsyncError";
import {fromEsFormat} from "../../util/fromEsFormat";
import {useClientContext} from "../../elastic/ClientContext";
import {FUNCTION_CATEGORY} from "../../content/Placeholder";
import {C10} from "../../style/Colors";
import {PersonFunctionCategory} from "../../elastic/model/PersonFunctionCategory";
import renderPlot from "../../common/plot/Plot";
import {usePlotContext} from "../../common/plot/PlotContext";
import {useLoadingContext} from "../../LoadingContext";
import {randStr} from "../../util/randStr";
import {usePrevious} from "../../hook/usePrevious";
import useSetLoadingWhen from "../../hook/useSetLoadingWhen";

moment.locale('nl');

type FunctionCategoryHistogramProps = {
  svgRef: MutableRefObject<any>,
  handleResolutions: (r: string[]) => void,
  personFunctionCategory: PersonFunctionCategory,
  memoKey: any
}

/**
 * Bar chart rendered on svgRef
 */
export const FunctionCategoryPlot = function (props: FunctionCategoryHistogramProps) {

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

    client.resolutionResource.aggregateByFunctionCategory(
      bars.reduce((all, arr: DataEntry) => all.concat(arr.ids), [] as string[]),
      props.personFunctionCategory,
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
        { color: C10, y: { title: props.personFunctionCategory.name, subtitle: FUNCTION_CATEGORY}},
        props.handleResolutions
      );
      setLoadingState({event: eventName, loading: false});
    }).catch(throwError);
  }

  return null;

};
