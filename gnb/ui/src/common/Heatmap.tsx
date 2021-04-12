import * as d3 from 'd3';
import {MutableRefObject} from 'react';
import heatmapTestdata from './heatmap-testdata.json';

export function renderHeatmap(
  canvasRef: MutableRefObject<any>,
  // bars: HistogramBar[],
  // config: HistogramConfig,
  // handleBarClick: (ids: string[]) => void
) {

  const data = heatmapTestdata;

  let result = new Map(data.map(value => [value['date'], value['count']]));

  const width = 960, height = 136, cellSize = 17;
  const color = d3.scaleQuantize<string>()
    .domain([0, 100])
    .range(['#f3f6e7', '#e7eecf', '#dbe5b7', '#d0dd9f', '#c4d587', '#b8cd6f', '#acc457', '#a1bc3f', '#94b327', '#89ab0f']);

  const start = data[0].date;
  const startDate = new Date(start);

  const end = data[data.length-1].date;
  const endDate = new Date(end);

  const svg = d3.select(canvasRef.current)
    .select(".d3-canvas")
    .select(".plot-area")
    .data([parseInt(start)])
    .attr('width', width)
    .attr('height', height)
    .append('g')
    .attr('transform', 'translate(' + ((width - cellSize * 53) / 2) + ',' + (height - cellSize * 7 - 1) + ')');

  svg.append('g')
    .attr('fill', 'none')
    .attr('stroke', '#000')
    .attr('stroke-width', '0.1px')
    .selectAll('rect')
    .data(d => {
      let startDateEdge = new Date(startDate);
      startDateEdge.setDate(startDate.getDate()-1)
      return d3.timeDays(startDateEdge, endDate);
    })
    .enter()
    .append('rect')
    .attr('width', cellSize)
    .attr('height', cellSize)
    .attr('x', d => d3.timeMonday.count(startDate, d) * cellSize)
    .attr('y', d => d.getUTCDay() * cellSize)
    .datum(d3.timeFormat('%Y-%m-%d'))
    .attr('fill', d => color(result.get(d) as number))
    .on('mouseover', function (e, d) {
      d3.select(this).attr('stroke-width', '1px');
    })
    .on('mouseout', function () {
      d3.select(this).attr('stroke-width', '0.1px');
    })
    .append('title')
    .text(d => d + ': ' + result.get(d) + '%')

  svg.append('text')
    .attr('transform', 'translate(-6,' + cellSize * 3.5 + ')rotate(-90)')
    .attr('font-family', 'sans-serif')
    .attr('font-size', '1em')
    .attr('text-anchor', 'middle')
    .text(d => d)

  svg.append('g')
    .attr('fill', 'none')
    .attr('stroke', '#000')
    .attr('stroke-width', '1.5px')
    .selectAll('path')
    .data(d => {
      const startMonthDate = new Date(startDate);
      startMonthDate.setDate(0);
      return d3.timeMonth.range(startMonthDate, endDate);
    })
    .enter()
    .append('path')
    .attr('d', function (startMonth) {
      if(startMonth < startDate) {
        startMonth.setDate(startDate.getDate());
      }
      const startWeekday = startMonth.getUTCDay();
      const startWeek = d3.timeMonday.count(startDate, startMonth);

      const endWeek = d3.timeMonday.count(startDate, endDate);
      const endWeekday = endDate.getUTCDay() - 1;

      return 'M' + (startWeek + 1) * cellSize + ',' + startWeekday * cellSize
        + 'H' + startWeek * cellSize + 'V' + 7 * cellSize
        + 'H' + endWeek * cellSize + 'V' + (endWeekday + 1) * cellSize
        + 'H' + (endWeek + 1) * cellSize + 'V' + 0
        + 'H' + (startWeek + 1) * cellSize + 'Z';
    });


}

function toStr(date: Date) {
  return date.getFullYear()
    + '-'
    + ('0' + (date.getMonth()+1)).slice(-2)
    + '-'
    + ('0' + date.getDate()).slice(-2)
}
