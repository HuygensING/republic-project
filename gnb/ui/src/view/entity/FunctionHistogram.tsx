import {memo, MutableRefObject} from "react";
import moment from "moment";
import 'moment/locale/nl'
import {DataEntry} from "../../common/plot/DataEntry";
import {useResolutionContext} from "../../resolution/ResolutionContext";
import {useAsyncError} from "../../hook/useAsyncError";
import {fromEsFormat} from "../../util/fromEsFormat";
import {useClientContext} from "../../elastic/ClientContext";
import {equal} from "../../util/equal";
import {FUNCTION} from "../../content/Placeholder";
import {C10} from "../../style/Colors";
import {PersonFunction} from "../../elastic/model/PersonFunction";
import {usePlotContext} from "../../common/plot/PlotContext";
import renderPlot from "../../common/plot/Plot";
import {usePrevious} from "../../hook/usePrevious";

moment.locale('nl');

type FunctionHistogramProps = {
  svgRef: MutableRefObject<any>,
  handleResolutions: (r: string[]) => void,
  personFunction: PersonFunction,
  memoKey: any
}

/**
 * Bar chart rendered on svgRef
 */
export const FunctionHistogram = function (props: FunctionHistogramProps) {

  const {resolutionState} = useResolutionContext();
  const throwError = useAsyncError();
  const client = useClientContext().clientState.client;
  const {plotState} = usePlotContext();

  if(usePrevious(props.memoKey) !== props.memoKey) updateHistogram();

  function updateHistogram() {

    const bars = resolutionState.resolutions;

    if (!bars.length) {
      return;
    }

    client.resolutionResource.aggregateByFunction(
      bars.reduce((all, arr: DataEntry) => all.concat(arr.ids), [] as string[]),
      props.personFunction,
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
        { color: C10, y: { title: props.personFunction.name, subtitle: FUNCTION}},
        props.handleResolutions
      );

    }).catch(throwError);
  }

  return null;

};
