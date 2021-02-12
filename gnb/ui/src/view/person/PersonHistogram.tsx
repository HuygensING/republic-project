import React, {memo, MutableRefObject} from "react";
import moment from "moment";
import 'moment/locale/nl'
import {HistogramBar, renderHistogram} from "../../common/Histogram";
import {useResolutionContext} from "../../resolution/ResolutionContext";
import {useAsyncError} from "../../hook/useAsyncError";
import {fromEsFormat} from "../../util/fromEsFormat";
import {Person, toName} from "../../elastic/model/Person";
import {useClientContext} from "../../search/ClientContext";
import {equal} from "../../util/equal";
import {PersonType, toPlaceholder} from "../../elastic/model/PersonType";
import {PERSON_HISTOGRAM_PREFIX} from "../../Placeholder";

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
export const PersonHistogram = memo(function(props: AttendantHistogramProps) {

  const {resolutionState} = useResolutionContext();
  const throwError = useAsyncError();
  const client = useClientContext().clientState.client;

  updateHistogram();
  function updateHistogram() {

    const bars = resolutionState.resolutions;

    if (!bars.length) {
      return;
    }

    client.resolutionResource.aggregateByPerson(
      bars.reduce((all, arr: HistogramBar) => all.concat(arr.ids), [] as string[]),
      props.person.id,
      props.type,
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
        {bar: {color: "orange"}, y: {title: `${PERSON_HISTOGRAM_PREFIX} ${toPlaceholder(props.type)} ${toName(props.person)}`}},
        props.handleResolutions
      );

    }).catch(throwError);
  }

  return null;

}, (prev, next) => equal(prev.memoKey, next.memoKey));
