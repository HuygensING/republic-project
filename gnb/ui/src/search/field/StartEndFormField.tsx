import React, {createElement, forwardRef, Ref, useEffect, useState} from "react";
import moment from "moment";
import useEvent from "../../hook/useEvent";
import {useSearchContext} from "../SearchContext";
import DatePicker, {registerLocale} from "react-datepicker";
import nl from "date-fns/locale/nl";

import "react-datepicker/dist/react-datepicker.css";
import {
  CALENDAR_MOVE_WITH_LEFT_ARROW,
  CALENDAR_MOVE_WITH_RIGHT_ARROW,
  HELP_BALLOON_PERIOD,
  WARN_DATEPICKER_END_BEFORE_START
} from "../../content/Placeholder";
import Warning from "../../common/Warning";
import PlotTypeFormField from "./PlotTypeFormField";
import {useLoading} from "../../LoadingContext";

const DATE_FORMAT = "yyyy-MM-dd";
const LOCALE_NL = "nl";

export default function StartEndFormField() {

  const {searchState, setSearchState} = useSearchContext();

  const [state, setState] = useState({
    warning: false,
    localeRegistered: false
  });

  function calcStepSize(start: Date, end: Date) {
    return Math.round(moment(end).diff(moment(start), 'days') / 10);
  }

  const start = searchState.start;
  const end = searchState.end;
  const stepSize = calcStepSize(start, end);
  const isLoadingState = useLoading();

  const handlePrevious = () => {
    const previous = (date: Date) => moment(date).subtract(stepSize, 'days').toDate();
    updateStartEnd(previous(searchState.start), previous(searchState.end));
  };

  const handleNext = () => {
    const next = (date: Date) => moment(date).add(stepSize, 'days').toDate();
    updateStartEnd(next(searchState.start), next(searchState.end));
  };

  const handlePickedStartDate = (newStart: Date) => {
    const diff = moment(newStart).diff(moment(start), 'days');
    const newEnd = moment(end).add(diff, 'days').toDate();
    updateStartEnd(newStart, newEnd);
  };

  const handlePickedEndDate = (newEnd: Date) => {
    if (newEnd < start) {
      setState({...state, warning: true});
      return;
    }
    updateStartEnd(start, newEnd);
  };

  function updateStartEnd(start: Date, end: Date) {
    setSearchState({...searchState, start, end});
  }

  useEffect(() => {
    registerLocale(LOCALE_NL, nl);
    setState(s => {return {...s, localeRegistered: true}})
  }, [setState]);

  useEvent('keyup', handleArrowKeys);
  function handleArrowKeys(e: React.KeyboardEvent<HTMLElement>) {
    if(isLoadingState) {
      return;
    }
    if ((e.target as any).tagName === "INPUT") {
      return;
    }
    if (e.key === 'ArrowLeft') {
      handlePrevious();
    }
    if (e.key === 'ArrowRight') {
      handleNext();
    }
  }

  function closeWarning() {
    setState({...state, warning: false});
  }

  return <>
    {state.warning ? <Warning msg={WARN_DATEPICKER_END_BEFORE_START} onClose={closeWarning}/> : null}
    <div className="input-group">
      <div className="input-group-prepend">
        <button
          type="button"
          className="btn btn-outline-secondary"
          onClick={handlePrevious}
          aria-label={CALENDAR_MOVE_WITH_LEFT_ARROW} data-balloon-pos="up-left"
        >
          <i className="fas fa-arrow-left"/>
        </button>
      </div>
      <div aria-label={HELP_BALLOON_PERIOD} data-balloon-pos="up">
        <DatePicker
          customInput={createElement(forwardRef(DatePickerCustomInput))}
          selected={start}
          onChange={handlePickedStartDate}
          dateFormat={DATE_FORMAT}
          locale={state.localeRegistered ? LOCALE_NL : undefined}
          showYearDropdown
          showMonthDropdown
        />
      </div>
      <div className="input-group-append">
        <span className="input-group-text">t/m</span>
      </div>
      <div aria-label={HELP_BALLOON_PERIOD} data-balloon-pos="up">
        <DatePicker
          customInput={createElement(forwardRef(DatePickerCustomInput))}
          selected={end}
          onChange={handlePickedEndDate}
          dateFormat={DATE_FORMAT}
          locale={state.localeRegistered ? LOCALE_NL : undefined}
          // TODO: clicking year dropdown results in error: 'findDOMNode is deprecated in StrictMode'
          showYearDropdown
          showMonthDropdown
        />
      </div>
      <div className="input-group-append">
        <button
          type="button"
          className="btn btn-outline-secondary"
          aria-label={CALENDAR_MOVE_WITH_RIGHT_ARROW} data-balloon-pos="up-right"
          onClick={handleNext}
        >
          <i className="fas fa-arrow-right"/>
        </button>
      </div>
      <PlotTypeFormField/>
    </div>
  </>;
}

const DatePickerCustomInput = (
  {value, onClick}: { value: string; onClick: (event: React.MouseEvent<HTMLButtonElement, MouseEvent>) => void },
  ref: Ref<HTMLButtonElement>
) => (
  <button
    type="button"
    className="form-control text-center stretched-link text-monospace"
    onClick={onClick}
    ref={ref}
  >
    {value} <i className="far fa-calendar-alt"/>
  </button>
);

