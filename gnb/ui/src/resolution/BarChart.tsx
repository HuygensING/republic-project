import {MutableRefObject} from "react";
import * as d3 from "d3";
import {ScaleBand} from "d3";
import {equal, usePrevious} from "../Util";
import {ResolutionDateEntry} from "../ResolutionDateEntry";
import {useSearchContext} from "../search/SearchContext";
import GnbElasticClient from "../elastic/GnbElasticClient";
import moment from "moment";
import 'moment/locale/nl'
import {useAsyncError} from "../useAsyncHook";

moment.locale('nl');

type BarChartProps = {
  client: GnbElasticClient,
  svgRef: MutableRefObject<any>,
  handleResolutions: (r: string[]) => void
}


/**
 * Bar chart rendered on svgRef
 */
export default function BarChart(props: BarChartProps) {

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
    console.log('createChart');
    return props.client.resolutionResource.aggregateBy(
      state.attendants.map(p => p.id),
      state.mentioned.map(p => p.id),
      state.start,
      state.end,
      state.fullText
    ).then((buckets: any) => {
      const data = buckets.map((b: any) => ({
        date: b.key_as_string,
        doc_count: b.doc_count,
        resolution_ids: b.resolution_ids.buckets.map((b: any) => b.key)
      }));
      renderChart(props.svgRef, data);
    }).catch(throwError);
  }

  function renderChart(ref: MutableRefObject<any>, chartData: ResolutionDateEntry[]) {
    let svg = d3.select(ref.current);

    const height = 500;
    const width = 500;
    const margin = {top: 20, right: 30, bottom: 30, left: 40};

    const x: ScaleBand<string> = d3
      .scaleBand()
      .domain(chartData.map(dataToBucket) as Iterable<string>)
      .rangeRound([margin.left, width - margin.right])
      .padding(0.1);

    function dataToBucket(d: ResolutionDateEntry) {
      return moment(d.date).format('D MMM');
    }

    const y1 = d3
      .scaleLinear()
      .domain([0, d3.max(chartData, (d) => d.doc_count)] as Iterable<number>)
      .rangeRound([height - margin.bottom, margin.top]);

    const xAxis = (graph: any) =>
      graph
        .attr("transform", `translate(0,${height - margin.bottom})`)
        .call(d3.axisBottom(x)
          .tickSizeOuter(0)
          .tickValues(x.domain().filter((d, i) => !(i % 10)))
        );

    const yAxisTicks = y1.ticks()
      .filter(tick => Number.isInteger(tick));

    const y1Axis = (graph: any) =>
      graph
        .attr("transform", `translate(${margin.left},0)`)
        .style("color", "black")
        .call(d3
          .axisLeft(y1)
          .tickValues(yAxisTicks)
          .tickFormat(d3.format('d'))
        )
        .call((graph: any) =>
          graph
            .append("text")
            .attr("x", -margin.left)
            .attr("y", 10)
            .attr("fill", "currentColor")
            .attr("text-anchor", "start")
            .text('# resoluties')
        );

    svg.select(".x-axis").call(xAxis);
    svg.select(".y-axis").call(y1Axis);
    svg
      .select(".plot-area")
      .attr("fill", "steelblue")
      .selectAll(".bar")
      .data(chartData)
      .join("rect")
      .attr("class", "bar clickable-bar clickable")
      .attr("x", (d: ResolutionDateEntry) => '' + x(dataToBucket(d)))
      .attr("width", x.bandwidth())
      .attr("y", (d: { doc_count: d3.NumberValue; }) => y1(d.doc_count))
      .attr("height", (d: { doc_count: d3.NumberValue; }) => y1(0) - y1(d.doc_count))
      .on("click", handleBarClick);

    function handleBarClick(e: any, d: any) {
      const date = chartData.find(cd => cd.date === d.date);
      const ids = date ? date.resolution_ids : [];
      props.handleResolutions(ids);
    }
  }

  return null;

};

