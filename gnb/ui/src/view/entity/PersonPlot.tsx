import {MutableRefObject} from "react";
import moment from "moment";
import 'moment/locale/nl'
import {DataEntry} from "../../common/plot/DataEntry";
import {useResolutionContext} from "../../resolution/ResolutionContext";
import {useAsyncError} from "../../hook/useAsyncError";
import {fromEsFormat} from "../../util/fromEsFormat";
import {useClientContext} from "../../elastic/ClientContext";
import {PersonType, toPlaceholder} from "../../elastic/model/PersonType";
import {Person} from "../../elastic/model/Person";
import {C6, C7} from "../../style/Colors";
import {usePlotContext} from "../../common/plot/PlotContext";
import renderPlot from "../../common/plot/Plot";
import {useLoadingContext} from "../../LoadingContext";
import {randStr} from "../../util/randStr";
import {usePrevious} from "../../hook/usePrevious";
import useSetLoadingWhen from "../../hook/useSetLoadingWhen";

moment.locale('nl');

type AttendantHistogramProps = {
  svgRef: MutableRefObject<any>,
  handleResolutions: (r: string[]) => void,
  person: Person,
  type: PersonType,
  memoKey: any
}

/**
 * Bar chart rendered on svgRef
 */
export const PersonPlot = function (props: AttendantHistogramProps) {

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

    const type = props.type;

    client.resolutionResource.aggregateByPerson(
      bars.reduce((all, arr: DataEntry) => all.concat(arr.ids), [] as string[]),
      props.person.id,
      type,
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
        {
          color: props.type === PersonType.ATTENDANT ? C6 : C7,
          y: {title: props.person.searchName, subtitle: `${toPlaceholder(type)}`}
        },
        props.handleResolutions
      );
      setLoadingState({event: eventName, loading: false});

    }).catch(throwError);
  }

  return null;

};
