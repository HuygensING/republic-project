import React from "react";

/**
 * Catching async errors with error boundaries using React.setState
 * See: https://medium.com/trabe/catching-asynchronous-errors-in-react-using-error-boundaries-5e8a5fd7b971
 */
export const useAsyncError = () => {
  const [, setError] = React.useState();
  return React.useCallback(
    e => {
      setError(() => {
        throw e;
      });
    },
    [setError],
  ) as (e: Error) => never;
};
