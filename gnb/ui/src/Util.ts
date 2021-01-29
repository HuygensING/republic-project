import {useEffect, useRef} from 'react';

export function equal<T>(prev: T, next: T) {
  return JSON.stringify(prev) === JSON.stringify(next);
}

export function usePrevious<T>(value: T): T {
  const ref = useRef(null as unknown as T);
  useEffect(() => {
    ref.current = value;
  });
  return ref.current;
}

export async function sleep(ms: number) {
  return new Promise(r => setTimeout(r, ms));
}

