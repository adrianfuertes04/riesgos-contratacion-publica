import { createContext, useContext, type ReactNode } from "react";

import type { Meta } from "./api";
import { useApi } from "./hooks";

const EMPTY: Meta = { disclaimer: "", indicators: {}, procedure: {}, contract_type: {}, buyer_type: {} };

const MetaContext = createContext<Meta>(EMPTY);

/** Etiquetas oficiales (listas CODICE) e indicadores, cargadas una vez desde /api/meta. */
export function MetaProvider({ children }: { children: ReactNode }) {
  const { data } = useApi<Meta>("/meta");
  return <MetaContext.Provider value={data ?? EMPTY}>{children}</MetaContext.Provider>;
}

export const useMeta = () => useContext(MetaContext);
