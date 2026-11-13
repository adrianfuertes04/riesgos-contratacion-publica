import { Link } from "react-router-dom";

import { enc, type Alert, type Contract, type Counterpart } from "../api";
import { fmtDate, fmtEur, fmtInt, fmtPct } from "../format";
import { Empty, RiskBadge } from "./ui";

const th = "px-2 py-2 text-left text-xs font-semibold uppercase tracking-wide text-slate-500";
const td = "px-2 py-2 align-top";

export function AlertsTable({ alerts, hideBuyer = false }: { alerts: Alert[]; hideBuyer?: boolean }) {
  if (!alerts.length) return <Empty>Sin alertas.</Empty>;
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="border-b border-slate-200">
          <tr>
            <th className={`${th} whitespace-nowrap`}>Indicador</th>
            {!hideBuyer && <th className={`${th} min-w-[12rem]`}>Órgano</th>}
            <th className={`${th} min-w-[11rem]`}>Empresa</th>
            <th className={`${th} whitespace-nowrap text-right`}>Importe</th>
            <th className={`${th} whitespace-nowrap`}>Fecha</th>
            <th className={`${th} min-w-[18rem]`}>Explicación</th>
            <th className={`${th} whitespace-nowrap`}>Riesgo</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {alerts.map((a, i) => (
            <tr key={`${a.indicator}-${a.contract_id ?? a.buyer_id}-${a.company_id}-${i}`}>
              <td className={`${td} whitespace-nowrap`}>
                <span className="mr-1 rounded bg-slate-100 px-1.5 py-0.5 font-mono text-xs">{a.indicator}</span>
                {a.indicator_name}
              </td>
              {!hideBuyer && (
                <td className={td}>
                  <Link className="text-sky-700 hover:underline" to={`/organismos/${enc(a.buyer_id)}`}>
                    {a.buyer_name}
                  </Link>
                </td>
              )}
              <td className={td}>
                {a.company_id ? (
                  <Link className="text-sky-700 hover:underline" to={`/empresas/${enc(a.company_id)}`}>
                    {a.company_name}
                  </Link>
                ) : (
                  "—"
                )}
              </td>
              <td className={`${td} whitespace-nowrap text-right tabular-nums`}>{fmtEur(a.amount)}</td>
              <td className={`${td} whitespace-nowrap tabular-nums`}>{fmtDate(a.ref_date)}</td>
              <td className={`${td} max-w-md text-slate-700`}>
                {a.explanation}{" "}
                {a.url && (
                  <a className="whitespace-nowrap text-sky-700 hover:underline" href={a.url} target="_blank" rel="noreferrer">
                    Ver en PLACSP ↗
                  </a>
                )}
              </td>
              <td className={`${td} whitespace-nowrap`}>
                <RiskBadge score={a.risk_score} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function ContractsTable({
  contracts,
  side,
  procedures,
}: {
  contracts: Contract[];
  side: "buyer" | "company";
  procedures: Record<string, string>;
}) {
  if (!contracts.length) return <Empty>Sin contratos.</Empty>;
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="border-b border-slate-200">
          <tr>
            <th className={`${th} min-w-[14rem]`}>Objeto</th>
            <th className={`${th} min-w-[12rem]`}>{side === "buyer" ? "Adjudicatario" : "Órgano"}</th>
            <th className={`${th} min-w-[9rem]`}>Procedimiento</th>
            <th className={`${th} whitespace-nowrap text-right`}>Ofertas</th>
            <th className={`${th} whitespace-nowrap text-right`}>Presupuesto</th>
            <th className={`${th} whitespace-nowrap text-right`}>Adjudicación</th>
            <th className={`${th} whitespace-nowrap`}>Fecha</th>
            <th className={`${th} whitespace-nowrap`}>Riesgo</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {contracts.map((c) => (
            <tr key={c.contract_id}>
              <td className={`${td} max-w-sm`}>
                {c.url ? (
                  <a className="text-sky-700 hover:underline" href={c.url} target="_blank" rel="noreferrer">
                    {c.title ?? c.entry_id}
                  </a>
                ) : (
                  c.title
                )}
                {c.lot_id && <span className="ml-1 text-xs text-slate-500">(lote {c.lot_id})</span>}
              </td>
              <td className={td}>
                {side === "buyer" ? (
                  <Link className="text-sky-700 hover:underline" to={`/empresas/${enc(c.company_id)}`}>
                    {c.winner_name}
                  </Link>
                ) : (
                  <Link className="text-sky-700 hover:underline" to={`/organismos/${enc(c.buyer_id)}`}>
                    {c.buyer_name}
                  </Link>
                )}
              </td>
              <td className={td}>{(c.procedure_code && procedures[c.procedure_code]) ?? c.procedure_code ?? "—"}</td>
              <td className={`${td} whitespace-nowrap text-right tabular-nums`}>{fmtInt(c.n_offers)}</td>
              <td className={`${td} whitespace-nowrap text-right tabular-nums`}>{fmtEur(c.budget)}</td>
              <td className={`${td} whitespace-nowrap text-right tabular-nums`}>{fmtEur(c.amount)}</td>
              <td className={`${td} whitespace-nowrap tabular-nums`}>{fmtDate(c.ref_date)}</td>
              <td className={`${td} whitespace-nowrap`}>
                <RiskBadge score={c.risk_score} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function CounterpartsTable({ rows, kind }: { rows: Counterpart[]; kind: "buyer" | "company" }) {
  if (!rows.length) return <Empty>Sin datos.</Empty>;
  const base = kind === "buyer" ? "/organismos/" : "/empresas/";
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="border-b border-slate-200">
          <tr>
            <th className={`${th} min-w-[12rem]`}>{kind === "buyer" ? "Órgano" : "Empresa"}</th>
            <th className={`${th} whitespace-nowrap text-right`}>Contratos</th>
            <th className={`${th} whitespace-nowrap text-right`}>Importe</th>
            <th className={`${th} whitespace-nowrap text-right`}>Cuota del órgano</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {rows.map((r) => (
            <tr key={r.id}>
              <td className={td}>
                <Link className="text-sky-700 hover:underline" to={`${base}${enc(r.id)}`}>
                  {r.name ?? r.id}
                </Link>
              </td>
              <td className={`${td} whitespace-nowrap text-right tabular-nums`}>{fmtInt(r.n_contracts)}</td>
              <td className={`${td} whitespace-nowrap text-right tabular-nums`}>{fmtEur(r.amount)}</td>
              <td className={`${td} whitespace-nowrap text-right tabular-nums`}>{fmtPct(r.share_of_buyer)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
