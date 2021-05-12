import {MutableRefObject, useEffect} from "react";
import {useSearchContext} from "../search/SearchContext";
import moment from "moment";
import 'moment/locale/nl'
import {useAsyncError} from "../hook/useAsyncError";
import {DataEntry} from "../common/plot/DataEntry";
import {usePrevious} from "../hook/usePrevious";
import {equal} from "../util/equal";
import {useResolutionContext} from "./ResolutionContext";
import {useClientContext} from "../elastic/ClientContext";
import {RESOLUTIONS_HISTOGRAM_TITLE} from "../content/Placeholder";
import {C9} from "../style/Colors";
import renderPlot from "../common/plot/Plot";
import {usePlotContext} from "../common/plot/PlotContext";
import {useLoadingContext} from "../LoadingContext";

moment.locale('nl');

type BarChartProps = {
  svgRef: MutableRefObject<any>,
  handleResolutions: (r: string[]) => void
}

/**
 * Bar chart rendered on svgRef
 */
export default function ResolutionPlot(props: BarChartProps) {

  const client = useClientContext().clientState.client;
  const {plotState} = usePlotContext();
  const {searchState} = useSearchContext();
  const {setLoadingState} = useLoadingContext();
  const {resolutionState, setResolutionState} = useResolutionContext();

  const throwError = useAsyncError();

  const prevSearchState = usePrevious(searchState);
  const prevResolutions = usePrevious(resolutionState.resolutions);
  const prevPlotState = usePrevious(plotState);

  const searchStateChanged = !equal(prevSearchState, searchState);
  const resolutionStateChanged = !equal(prevResolutions, resolutionState.resolutions);
  const plotStateChanged = !equal(prevPlotState, plotState);

  useEffect(() => {
    setLoadingState({resolutionsLoading: true});
  }, [searchStateChanged, setLoadingState])

  if (searchStateChanged) {
    updateResolutions();
  } else if (resolutionStateChanged || plotStateChanged) {
    updatePlot();
  }

  return null;

  function updateResolutions() {

    const attendants = searchState.attendants.map(p => p.id);
    const mentioned = searchState.mentioned.map(p => p.id);

    client.resolutionResource.aggregateBy(
      attendants,
      mentioned,
      searchState.start,
      searchState.end,
      searchState.fullText,
      searchState.places,
      searchState.functions,
      searchState.functionCategories
    ).then((buckets: any) => {
      const bars = buckets.map((b: any) => ({
        date: b.key_as_string,
        count: b.doc_count,
        ids: b.resolution_ids.buckets.map((b: any) => b.key)
      } as DataEntry));
      setResolutionState({...resolutionState, resolutions: bars});
      setLoadingState({resolutionsLoading: false});
    }).catch(throwError);
  }

  function updatePlot() {
    renderPlot(
      plotState.type,
      props.svgRef,
      resolutionState.resolutions,
      {color: C9, y: {title: RESOLUTIONS_HISTOGRAM_TITLE}},
      props.handleResolutions
    );
  }

};

