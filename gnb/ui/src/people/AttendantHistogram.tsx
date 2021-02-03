import {MutableRefObject} from "react";
import GnbElasticClient from "../elastic/GnbElasticClient";
import moment from "moment";
import 'moment/locale/nl'
import {renderHistogram} from "../common/Histogram";
import {usePrevious} from "../hook/usePrevious";
import {equal} from "../util/equal";
import {useResolutionContext} from "../resolution/ResolutionContext";

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

  if(resolutionStateChanged) {
    updateHistogram();
  }

  function updateHistogram() {
    renderHistogram(
      props.svgRef,
      resolutionState.resolutions,
      props.handleResolutions
    );
  }

  return null;

};

