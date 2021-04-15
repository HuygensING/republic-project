import * as d3 from 'd3';
import {ScaleBand} from 'd3';
import moment from 'moment';
import {MutableRefObject} from 'react';
import {PlotConfig} from './PlotConfig';
import {getTooltip, showTooltip} from "./D3Canvas";
import {DataEntry} from "./DataEntry";

export function renderHistogram(
  canvasRef: MutableRefObject<any>,
  bars: DataEntry[],
  config: PlotConfig,
  handleBarClick: (ids: string[]) => void
) {

  let svg = d3
    .select(canvasRef.current)
    .select('.d3-canvas');

  const svgSize = canvasRef.current.getBoundingClientRect();
  const height = svgSize.height;
  const width = svgSize.width;
  const margin = {top: 20, right: 30, bottom: 30, left: 40};

  const x: ScaleBand<string> = d3
    .scaleBand()
    .domain(bars.map(dataToBucket) as Iterable<string>)
    .range([margin.left, width - margin.right])
    .padding(0.1);

  function dataToBucket(d: DataEntry) {
    return moment(d.date).format('DD-MM-YYYY');
  }

  const y1 = d3
    .scaleLinear()
    .domain([0, d3.max(bars, (d) => d.count)] as Iterable<number>)
    .rangeRound([height - margin.bottom, margin.top]);

  const xAxis = (graph: any) => {
    const tickInterval = Math.round(bars.length / 10);
    return graph
      .attr('transform', `translate(0,${height - margin.bottom})`)
      .call(d3.axisBottom(x)
        .tickSizeOuter(0)
        .tickValues(x.domain().filter((d, i) => !(i % tickInterval)))
      );
  };

  const yAxisTicks = y1.ticks()
    .filter(tick => Number.isInteger(tick));

  const y1Axis = (graph: any) => {
    return graph
      .attr('transform', `translate(${margin.left},0)`)
      .style('color', 'black')
      .call(d3
        .axisLeft(y1)
        .tickValues(yAxisTicks)
        .tickFormat(d3.format('d'))
      )
      .call((graph: any) =>
        graph
          .append('text')
          .attr('x', -margin.left)
          .attr('y', 10)
          .attr('fill', 'currentColor')
          .attr('text-anchor', 'start')
          .text(config.y.title)
      );
  };

  svg.select('.x-axis').call(xAxis);
  svg.select('.y-axis').call(y1Axis);

  svg
    .select('.plot-area')
    .attr('fill', config.color)
    .selectAll('.bar')
    .data(bars)
    .join('rect')
    .attr('class', 'bar clickable-bar clickable')
    .attr('x', (d: DataEntry) => '' + x(dataToBucket(d)))
    .attr('width', x.bandwidth())
    .attr('y', (d: { count: d3.NumberValue; }) => y1(d.count))
    .attr('height', (d: { count: d3.NumberValue; }) => y1(0) - y1(d.count))
    .on('mouseover', (e, d) => {
      const yPos = Math.round(y1(d.count));
      const barRect = e.target.getBoundingClientRect();
      const xPos = Math.round(barRect.left + barRect.width/2);
      showTooltip(canvasRef, `${d.date} (${d.count}x)`, config.color, xPos, yPos);
    })
    .on('mouseout', d => {
      getTooltip(canvasRef)
        .transition()
        .style('visibility', 'hidden');
    })
    .on('click', handleClick);

  function handleClick(e: any, d: any) {
    const date = bars.find(cd => cd.date === d.date);
    const ids = date ? date.ids : [];
    handleBarClick(ids);
  }
}
