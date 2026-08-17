import { useEffect, useState } from "react";

import { ApiClientError } from "../api/client";

interface AsyncState<T> {
  data: T | null;
  loading: boolean;
  error: ApiClientError | null;
}

export function useAsyncResource<T>(loader: (signal: AbortSignal) => Promise<T>): AsyncState<T> {
  const [state, setState] = useState<AsyncState<T>>({
    data: null,
    loading: true,
    error: null
  });

  useEffect(() => {
    const controller = new AbortController();
    setState((current) => ({ ...current, loading: true, error: null }));
    loader(controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) {
          setState({ data, loading: false, error: null });
        }
      })
      .catch((error: unknown) => {
        if (!controller.signal.aborted) {
          setState({
            data: null,
            loading: false,
            error:
              error instanceof ApiClientError
                ? error
                : new ApiClientError("Unexpected client error.", {
                    code: "CLIENT_ERROR",
                    status: null
                  })
          });
        }
      });
    return () => controller.abort();
  }, [loader]);

  return state;
}
