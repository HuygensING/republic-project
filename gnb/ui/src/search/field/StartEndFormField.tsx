import React, {createElement, forwardRef, Ref, useState} from "react";
import moment from "moment";
import useEvent from "../../hook/useEvent";
import {useSearchContext} from "../SearchContext";
import DatePicker from "react-datepicker";

import "react-datepicker/dist/react-datepicker.css";
import {WARN_DATEPICKER_END_BEFORE_START} from "../../Placeholder";
import Warning from "../../common/Warning";

export default function StartEndFormField() {

  const {searchState, setSearchState} = useSearchContext();
  const [state, setState] = useState({
    warning: false
  });

  function calcStepSize(start: Date, end: Date) {
    return Math.round(moment(start).diff(moment(end), 'days') / 10);
  }

  const start = searchState.start;
  const end = searchState.end;
  const stepSize = calcStepSize(start, end);

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
      setState({...state, warning : true});
      return;
    }
    updateStartEnd(start, newEnd);
  };

  function updateStartEnd(start: Date, end: Date) {
    setSearchState({...searchState, start, end});
  }

  useEvent('keyup', handleArrowKeys);

  function handleArrowKeys(e: React.KeyboardEvent<HTMLElement>) {
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
    setState({...state, warning : false});
  }

  return <>
    {state.warning ? <Warning msg={WARN_DATEPICKER_END_BEFORE_START} onClose={closeWarning}/> : null}
    <div className="input-group">
      <div className="input-group-prepend">
        <button
          type="button"
          className="btn btn-outline-secondary"
          onClick={handlePrevious}
        >
          &lt;&lt;
        </button>
      </div>
      <DatePicker
        customInput={createElement(forwardRef(DatePickerCustomInput))}
        selected={start}
        onChange={handlePickedStartDate}
      />
      <div className="input-group-append">
        <span className="input-group-text">t/m</span>
      </div>
      <DatePicker
        customInput={createElement(forwardRef(DatePickerCustomInput))}
        selected={end}
        onChange={handlePickedEndDate}
      />
      <div className="input-group-append">
        <button
          type="button"
          className="btn btn-outline-secondary"
          onClick={handleNext}
        >
          &gt;&gt;
        </button>
      </div>
    </div>
  </>;
}

const DatePickerCustomInput = (
  {value, onClick}: { value: string; onClick: (event: React.MouseEvent<HTMLButtonElement, MouseEvent>) => void },
  ref: Ref<HTMLButtonElement>
) => (
  <button type="button" className="form-control text-center stretched-link text-monospace" onClick={onClick}
          ref={ref}>{value} 📅</button>
);

