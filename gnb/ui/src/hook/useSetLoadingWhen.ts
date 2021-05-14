import React, {useEffect} from "react";
import {LoadingContext} from "../LoadingContext";

/**
 * Update loading state when condition is met
 *
 * @param event: string
 * @param loading: boolean
 * @param condition?: boolean set loading when condition is true or undefined
 */
export default function useSetLoadingWhen(
  event: string,
  loading: boolean,
  condition: boolean
) {
  const {setLoadingState} = React.useContext(LoadingContext);
  useEffect(() => {
    if (condition) {
      setLoadingState({event, loading});
    }
  }, [condition, setLoadingState]);
}

