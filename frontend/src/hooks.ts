import { useEffect, useState } from "react";

import { get } from "./api";

type Params = Record<string, string | number | null | undefined>;

export interface Loadable<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
}

/** Carga un recurso de la API y lo recarga cuando cambian la ruta o los parámetros. */
export function useApi<T>(path: string | null, params: Params = {}): Loadable<T> {
  const [state, setState] = useState<Loadable<T>>({ data: null, error: null, loading: path !== null });
  const key = JSON.stringify([path, params]);

  useEffect(() => {
    if (path === null) {
      setState({ data: null, error: null, loading: false });
      return;
    }
    let cancelled = false;
    setState((s) => ({ ...s, loading: true, error: null }));
    get<T>(path, params)
      .then((data) => !cancelled && setState({ data, error: null, loading: false }))
      .catch((e: Error) => !cancelled && setState({ data: null, error: e.message, loading: false }));
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  return state;
}
