import * as d3 from 'd3';
import {MutableRefObject} from 'react';
import {DataEntry} from "./Histogram";
import {getTooltip, showTooltip} from "./D3Canvas";
import {PlotConfig} from "./PlotConfig";

export function renderHeatmap(
  canvasRef: MutableRefObject<any>,
  data: DataEntry[],
  config: PlotConfig,
  handleDayClick: (ids: string[]) => void
) {

  const result = new Map(data.map(value => [value['date'], value['count']]));

  const start = data[0].date;
  const startDate = new Date(start);
  const end = data[data.length - 1].date;
  const endDate = new Date(end);
  const startMonthDate = new Date(startDate);
  startMonthDate.setDate(0);

  const svg = d3
    .select(canvasRef.current)
    .select('.d3-canvas');

  const margin = {top: 20, right: 30, bottom: 20, left: 20};
  const svgSize = canvasRef.current.getBoundingClientRect();
  const height = svgSize.height;
  const width = svgSize.width;

  const monthRange = d3.timeMonth.range(startMonthDate, endDate);
  const columns = d3.timeMonday.count(startDate, endDate);

  const cellWidth = (width - margin.left - monthRange.length * 2) / (columns + 1);
  const cellHeight = height / 8;

  const opacity = d3.scaleQuantize<number>()
    .domain([0, 30])
    .range([0.05, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1]);

  const plot = svg.select(".plot-area");

  // Size:
  plot.data([parseInt(start)])
    .attr('width', width)
    .attr('height', height)
    .attr('transform', `translate(${margin.left},1)`);

  // Cell outlines:
  const cells = plot
    .selectAll('.cell')
    .attr('fill', 'none')
    .attr('stroke', '#000')
    .attr('stroke-width', '0.1px')
    .data(() => {
      let startDateEdge = new Date(startDate);
      startDateEdge.setDate(startDate.getDate() - 1)
      return d3.timeDays(startDateEdge, endDate);
    });

  // Cell contents and interaction:
  cells
    .join('rect')
    .attr("class", "cell clickable-cell clickable")
    .attr('width', cellWidth)
    .attr('height', cellHeight)
    .attr('x', d => d3.timeMonday.count(startDate, d) * cellWidth)
    .attr('y', d => d.getUTCDay() * cellHeight)
    .datum(d3.timeFormat('%Y-%m-%d'))
    .attr('fill', () => config.color)
    .attr('opacity', d => opacity(result.get(d) as number))
    .on('mouseover', function (e, d) {
      let weekDay = new Date(d).getUTCDay();
      // Sunday should be 7 instead of 0:
      if (!weekDay) weekDay = 7;
      const yPos = weekDay * cellHeight;
      const barRect = e.target.getBoundingClientRect();
      const xPos = Math.round(barRect.left + barRect.width / 2);
      showTooltip(canvasRef, `${d}: ${result.get(d)}x`, config.color, xPos, yPos)
    })
    .on('mouseout', function () {
      d3.select(this).attr('stroke-width', '0.1px');
      getTooltip(canvasRef)
        .transition()
        .style('visibility', 'hidden');
    })
    .on('click', handleClick);

  // Y-label:
  plot
    .selectAll('.heatmap-y-label')
    .data([startDate])
    .join('text')
    .attr('class', 'heatmap-y-label')
    .attr('transform', 'translate(-6,' + cellHeight * 3.5 + ')rotate(-90)')
    .attr('text-anchor', 'middle')
    .text(() => {
      const y1 = startDate.getFullYear();
      const y2 = endDate.getFullYear();
      return y1 === y2 ? `${y1}` : `${y1} - ${y2}`;
    });

  // Outlined months:
  plot.selectAll('.month')
    .data(monthRange)
    .join('path')
    .attr('class', 'month')
    .attr('fill', 'none')
    .attr('stroke', '#000')
    .attr('stroke-width', '1.5px')
    .attr('d', function (startMonth) {
      if (startMonth < startDate) {
        startMonth.setDate(startDate.getDate());
      }
      const startWeekday = startMonth.getUTCDay();
      const startWeek = d3.timeMonday.count(startDate, startMonth);

      const endWeek = d3.timeMonday.count(startDate, endDate);
      const endWeekday = endDate.getUTCDay() - 1;

      return 'M' + (startWeek + 1) * cellWidth + ',' + startWeekday * cellHeight
        + 'H' + startWeek * cellWidth + 'V' + 7 * cellHeight
        + 'H' + endWeek * cellWidth + 'V' + (endWeekday + 1) * cellHeight
        + 'H' + (endWeek + 1) * cellWidth + 'V' + 0
        + 'H' + (startWeek + 1) * cellWidth + 'Z';
    });

  // Month labels:
  plot
    .selectAll('.month-label')
    .data(monthRange)
    .join('text')
    .attr('class', 'month-label')
    .attr(`transform`, (d) => `translate(${d3.timeMonday.count(startDate, d) * cellWidth}, ${height - 5})`)
    .attr('visibility', (d, i) => {
      const currentPos = d3.timeMonday.count(startDate, monthRange[i]);
      const nextPos = d3.timeMonday.count(startDate, monthRange[i + 1]);
      const overlappingLabelPosition = currentPos === nextPos;
      return overlappingLabelPosition ? 'hidden' : 'visible';
    })
    .text(d => d.toLocaleString('nl', {month: 'short'}));

  function handleClick(e: any, d: any) {
    const date = data.find(di => di.date === d);
    const ids = date ? date.ids : [];
    handleDayClick(ids);
  }

}

