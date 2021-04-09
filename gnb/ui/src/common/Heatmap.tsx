import * as d3 from 'd3';
import {MutableRefObject} from 'react';

export function renderHeatmap(
  canvasRef: MutableRefObject<any>,
  // bars: HistogramBar[],
  // config: HistogramConfig,
  // handleBarClick: (ids: string[]) => void
) {

  const data = {Data: [{date: '2021-01-02', count: 30}, {date: '2021-01-03', count: 60}]};

  console.log(data['Data'])

  let result = new Map(data['Data'].map(value => [value['date'], value['count']]));

  console.log('result', result);

  const width = 960, height = 136, cellSize = 17;
  const color = d3.scaleQuantize<string>()
    .domain([0, 100])
    .range(['#f3f6e7', '#e7eecf', '#dbe5b7', '#d0dd9f', '#c4d587', '#b8cd6f', '#acc457', '#a1bc3f', '#94b327', '#89ab0f']);

  console.log('color', color);

  const start = parseInt(data['Data'][0]['date']);
  const end = start + 1;
  console.log('start, end', start, end);
  const svg = d3.select(canvasRef.current)
    .select(".d3-canvas")
    .select(".plot-area")
    .data(d3.range(start, end))
    .attr('width', width)
    .attr('height', height)
    .append('g')
    .attr('transform', 'translate(' + ((width - cellSize * 53) / 2) + ',' + (height - cellSize * 7 - 1) + ')');

  svg.append('g')
    .attr('fill', 'none')
    .attr('stroke', '#000')
    .attr('stroke-width', '0.1px')
    .selectAll('rect')
    .data(d => d3.timeDays(new Date(d, 0, 1), new Date(d + 1, 0, 1)))
    .enter().append('rect')
    .attr('width', cellSize)
    .attr('height', cellSize)
    .attr('x', d => d3.timeMonday.count(d3.timeYear(d), d) * cellSize)
    .attr('y', d => d.getUTCDay() * cellSize)
    .datum(d3.timeFormat('%Y-%m-%d'))
    .attr('fill', d => color(result.get(d) as number))
    .on('mouseover', function () {
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
    .data(d => d3.timeMonths(new Date(d, 0, 1), new Date(d + 1, 0, 1)))
    .enter().append('path')
    .attr('d', function (d) {
      const t1 = new Date(d.getFullYear(), d.getMonth() + 1, 0),
        d0 = d.getUTCDay(), w0 = d3.timeMonday.count(d3.timeYear(d), d),
        d1 = t1.getUTCDay(), w1 = d3.timeMonday.count(d3.timeYear(t1), t1);
      return 'M' + (w0 + 1) * cellSize + ',' + d0 * cellSize
        + 'H' + w0 * cellSize + 'V' + 7 * cellSize
        + 'H' + w1 * cellSize + 'V' + (d1 + 1) * cellSize
        + 'H' + (w1 + 1) * cellSize + 'V' + 0
        + 'H' + (w0 + 1) * cellSize + 'Z';
    });


}
