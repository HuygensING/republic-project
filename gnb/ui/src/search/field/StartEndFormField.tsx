import React, {createElement, forwardRef, Ref} from "react";
import moment from "moment";
import useEvent from "../../UseEvent";
import {useSearchContext} from "../SearchContext";
import DatePicker from "react-datepicker";

import "react-datepicker/dist/react-datepicker.css";

export default function StartEndFormField() {

  const stepSize = 3;
  const {state, setState} = useSearchContext();
  const start = state.start;
  const end = state.end;

  const handlePrevious = () => {
    const previous = (date: Date) => moment(date).subtract(stepSize, 'days').toDate();
    updateStartEnd(previous(state.start), previous(state.end));
  };

  const handleNext = () => {
    const next = (date: Date) => moment(date).add(stepSize, 'days').toDate();
    updateStartEnd(next(state.start), next(state.end));
  };

  const handlePickedDate = (newStart: Date) => {
    const diff = moment(newStart).diff(moment(start), 'days');
    const newEnd = moment(end).add(diff, 'days').toDate();
    updateStartEnd(newStart, newEnd);
  };

  function updateStartEnd(start: Date, end: Date) {
    setState({...state, start, end});
  }

  useEvent('keyup', handleArrowKeys);

  function handleArrowKeys(e: React.KeyboardEvent<HTMLElement>) {
    if((e.target as any).tagName === "INPUT") {
      return;
    }
    if (e.key === 'ArrowLeft') {
      handlePrevious();
    }
    if (e.key === 'ArrowRight') {
      handleNext();
    }
  }

  return <div className="input-group">
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
        onChange={handlePickedDate}
      />
      <div className="input-group-append">
        <span className="input-group-text">t/m</span>
      </div>
      <DatePicker
        customInput={createElement(forwardRef(DatePickerDisabledInput))}
        disabled
        selected={end}
        onChange={() => {}}
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
    </div>;
}

const DatePickerCustomInput = (
  {value, onClick}: { value: string; onClick: (event: React.MouseEvent<HTMLButtonElement, MouseEvent>) => void },
  ref: Ref<HTMLButtonElement>
) => (
  <button type="button" className="form-control text-center stretched-link text-monospace" onClick={onClick} ref={ref}>{value} 📅</button>
);

const DatePickerDisabledInput = (
  {value, onClick}: { value: string; onClick: (event: React.MouseEvent<HTMLInputElement, MouseEvent>) => void },
  ref: Ref<HTMLInputElement>
) => (
  <span className="form-control disabled-input text-center text-monospace" ref={ref}>{value}</span>
);
