// Formatos en español.

const eur = new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR", maximumFractionDigits: 0 });
const eurCompact = new Intl.NumberFormat("es-ES", {
  style: "currency",
  currency: "EUR",
  notation: "compact",
  maximumFractionDigits: 1,
});
const int = new Intl.NumberFormat("es-ES");

export const fmtEur = (v: number | null | undefined) => (v == null ? "—" : eur.format(v));
export const fmtEurShort = (v: number | null | undefined) => (v == null ? "—" : eurCompact.format(v));
export const fmtInt = (v: number | null | undefined) => (v == null ? "—" : int.format(v));
export const fmtPct = (v: number | null | undefined, digits = 1) =>
  v == null ? "—" : `${(v * 100).toLocaleString("es-ES", { maximumFractionDigits: digits })} %`;
export const fmtScore = (v: number | null | undefined) => (v == null ? "—" : Math.round(v).toString());
export const fmtDate = (v: string | null | undefined) =>
  v ? new Date(`${v}T00:00:00`).toLocaleDateString("es-ES") : "—";
