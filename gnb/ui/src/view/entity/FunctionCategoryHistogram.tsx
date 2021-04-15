import {memo, MutableRefObject} from "react";
import moment from "moment";
import 'moment/locale/nl'
import {DataEntry} from "../../common/plot/Histogram";
import {useResolutionContext} from "../../resolution/ResolutionContext";
import {useAsyncError} from "../../hook/useAsyncError";
import {fromEsFormat} from "../../util/fromEsFormat";
import {useClientContext} from "../../elastic/ClientContext";
import {equal} from "../../util/equal";
import {FUNCTION_CATEGORY, HISTOGRAM_PREFIX} from "../../content/Placeholder";
import {C10} from "../../style/Colors";
import {PersonFunctionCategory} from "../../elastic/model/PersonFunctionCategory";
import renderPlot from "../../common/plot/Plot";
import {usePlotContext} from "../../common/plot/PlotContext";

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
export const FunctionCategoryHistogram = memo(function (props: FunctionCategoryHistogramProps) {

  const {resolutionState} = useResolutionContext();
  const throwError = useAsyncError();
  const client = useClientContext().clientState.client;
  const {plotState} = usePlotContext();

  updateHistogram();

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
        { color: C10, y: { title: `${HISTOGRAM_PREFIX} ${FUNCTION_CATEGORY}: ${props.personFunctionCategory.name}`}},
        props.handleResolutions
      );

    }).catch(throwError);
  }

  return null;

}, (prev, next) => equal(prev.memoKey, next.memoKey));
