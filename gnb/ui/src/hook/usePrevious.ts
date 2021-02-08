import {useEffect, useRef} from "react";

export function usePrevious<T>(value: T): T {
  const ref = useRef(null as unknown as T);
  useEffect(() => {
    ref.current = value;
  });
  return ref.current;
}
