import * as d3 from 'd3';
import {MutableRefObject} from 'react';
import {DataEntry} from "./DataEntry";
import {getTooltip, showTooltip} from "./D3Canvas";
import {PlotConfig} from "./PlotConfig";

/**
 * Original example: https://itnext.io/d3-v6-calendar-heat-map-c709fe20e737
 */
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

  const margin = {left: 35};
  const svgSize = canvasRef.current.getBoundingClientRect();
  const height = svgSize.height;
  const width = svgSize.width;

  const monthRange = d3.timeMonth.range(startMonthDate, endDate);
  const columns = d3.timeMonday.count(startDate, endDate);

  const cellWidth = (width - margin.left - monthRange.length * 2) / (columns + 1);
  const cellHeight = height / 8;

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
    .data(() => {
      let startDateEdge = new Date(startDate);
      startDateEdge.setDate(startDate.getDate() - 1)
      return d3.timeDays(startDateEdge, endDate);
    });

  const opacity = d3.scaleSqrt<number>()
    .domain([0, 40])
    .range([0, 1]);
  const round = d3.format(".2f");

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
    .attr('opacity', d => round(opacity(result.get(d) as number)))
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

  const title = config.y.title;
  const y1 = startDate.getFullYear();
  const y2 = endDate.getFullYear();
  const subtitle = `(${config.y.subtitle ? config.y.subtitle + ', ' : ''}${y1}${y1 === y2 ? '' : '-' + y2})`;

  // Y-labels:
  plot
    .selectAll('.heatmap-y-label')
    .data([subtitle, title])
    .join('text')
    .attr('class', 'heatmap-y-label')
    .attr('transform', (d, i) => `translate(${-8 + -15 * (i)},${cellHeight * 3.5})rotate(-90)`)
    .attr('text-anchor', 'middle')
    .text(d => d.length > 45 ? d.substr(0, 45) + '[..]' : d)
    .style('font-size', d => d.length > 40 ? 9 : 12);

  // Outlined months:
  plot.selectAll('.month')
    .data(monthRange)
    .join('path')
    .attr('class', 'month')
    .attr('fill', 'none')
    .attr('stroke', '#666')
    .attr('stroke-width', '1px')
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
        + 'H' + (endWeekday === -1 ? endWeek + 1 : endWeek) * cellWidth + 'V' + (endWeekday + 1) * cellHeight
        + 'H' + (endWeek + 1) * cellWidth + 'V' + 0
        + 'H' + (startWeek + 1) * cellWidth + 'Z';
    });

  // Month labels:
  const monthsToLabel = plot
    .selectAll('.month-label')
    .data(monthRange)
    .join('text')
    .attr('class', 'month-label')
    .attr(`transform`, (d) => `translate(${d3.timeMonday.count(startDate, d) * cellWidth}, ${height - 18})`)
    .attr('visibility', (d, i) => {
      const currentPos = d3.timeMonday.count(startDate, monthRange[i]);
      const nextPos = d3.timeMonday.count(startDate, monthRange[i + 1]);
      const overlappingLabelPosition = currentPos === nextPos;
      return overlappingLabelPosition ? 'hidden' : 'visible';
    });

  monthsToLabel
    .text('')
    .append('tspan')
    .text(d => d.toLocaleString('nl', {month: 'short'})).append('tspan')
    .attr('x', 0)
    .attr('dy', '1.4em');
  monthsToLabel
    .append('tspan')
    .text(d => {
      if (d.getMonth() === 0) {
        return d.getFullYear();
      } else {
        return '';
      }
    })
    .attr('x', 0)
    .attr('dy', '1.2em');

  function handleClick(e: any, d: any) {
    const date = data.find(di => di.date === d);
    const ids = date ? date.ids : [];
    handleDayClick(ids);
  }

}

