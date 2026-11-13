import { Link, useParams } from "react-router-dom";

import { enc, type BuyerProfile } from "../api";
import { AlertsTable, ContractsTable, CounterpartsTable } from "../components/tables";
import { Card, Disclaimer, Kpi, RiskBadge, Status } from "../components/ui";
import { fmtEur, fmtEurShort, fmtInt, fmtPct } from "../format";
import { useApi } from "../hooks";
import { useMeta } from "../meta";

/** Semáforo de una tasa: el color solo orienta, no es un umbral legal. */
function RateRow({ label, value, note }: { label: string; value: number | null; note?: string }) {
  const tone = value == null ? "bg-slate-200" : value >= 0.5 ? "bg-red-500" : value >= 0.2 ? "bg-amber-400" : "bg-emerald-500";
  return (
    <li className="flex items-center justify-between gap-3 py-1.5">
      <span className="flex items-center gap-2">
        <span className={`inline-block h-2.5 w-2.5 rounded-full ${tone}`} />
        {label}
        {note && <span className="text-xs text-slate-400">{note}</span>}
      </span>
      <span className="tabular-nums">{fmtPct(value)}</span>
    </li>
  );
}

export default function BuyerPage() {
  const { id = "" } = useParams();
  const meta = useMeta();
  const { data, loading, error } = useApi<BuyerProfile>(`/buyers/${enc(id)}`);
  const b = data?.buyer;

  return (
    <div className="space-y-6">
      <Status loading={loading} error={error} />
      {b && data && (
        <>
          <div>
            <div className="text-xs uppercase tracking-wide text-slate-500">Órgano de contratación</div>
            <h1 className="text-xl font-semibold">{b.name}</h1>
            <div className="mt-1 text-sm text-slate-600">
              NIF {b.nif ?? "—"} · {b.type_code ? meta.buyer_type[b.type_code] ?? b.type_code : "—"} · {b.city ?? "—"}{" "}
              {b.postal_code && `(${b.postal_code})`}
            </div>
            {b.hierarchy && <div className="mt-1 text-xs text-slate-500">{b.hierarchy}</div>}
            <Link className="mt-2 inline-block text-sm text-sky-700 hover:underline" to={`/grafo?node=buyer:${enc(b.buyer_id)}`}>
              Ver en el explorador de grafo →
            </Link>
          </div>
          <Disclaimer />
          <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
            <Kpi label="Contratos" value={fmtInt(b.n_contracts)} />
            <Kpi label="Importe" value={fmtEurShort(b.amount)} />
            <Kpi label="Empresas distintas" value={fmtInt(b.n_companies)} />
            <Kpi label="HHI (0-10.000)" value={b.hhi == null ? "—" : fmtInt(Math.round(b.hhi))} hint={`Principal: ${fmtPct(b.top_company_share)} del importe`} />
            <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
              <div className="text-xs font-medium uppercase tracking-wide text-slate-500">Puntuación de riesgo</div>
              <div className="mt-2">
                <RiskBadge score={b.risk_score} />
              </div>
              <div className="mt-1 text-xs text-slate-500">
                {b.eligible ? "Percentil medio frente a órganos comparables" : "Pocos contratos para puntuar"}
              </div>
            </div>
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <Card title="Indicadores">
              <ul className="divide-y divide-slate-100 text-sm">
                <RateRow label="I1 Único licitador" value={b.single_bidder_rate} note={`(${fmtInt(b.n_open)} abiertos)`} />
                <RateRow label="I3 Posible fraccionamiento" value={b.splitting_rate} note={`(${fmtInt(b.n_minor)} menores)`} />
                <RateRow label="I4 Procedimiento poco competitivo" value={b.non_competitive_rate} />
                <RateRow label="I5 Plazo corto" value={b.short_deadline_rate} />
                <RateRow label="I6 Precio anómalo" value={b.price_rate} />
                <RateRow label="I7 Contratos modificados" value={b.modified_rate} />
                <RateRow label="Peso medio de criterios de juicio de valor" value={b.subjective_share_avg} />
              </ul>
              {b.f_concentration && (
                <p className="mt-2 rounded bg-red-50 p-2 text-xs text-red-800">
                  I2: concentración de adjudicaciones en el percentil 95 o superior entre órganos comparables.
                </p>
              )}
            </Card>
            <Card title="Principales adjudicatarios">
              <CounterpartsTable rows={data.companies} kind="company" />
            </Card>
          </div>

          <Card title="Sectores (división CPV)">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="border-b border-slate-200 text-xs uppercase text-slate-500">
                  <tr>
                    <th className="min-w-[14rem] px-2 py-2 text-left">CPV</th>
                    <th className="whitespace-nowrap px-2 py-2 text-right">Contratos</th>
                    <th className="whitespace-nowrap px-2 py-2 text-right">Importe</th>
                    <th className="whitespace-nowrap px-2 py-2 text-right">HHI</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {data.cpv.map((c) => (
                    <tr key={c.cpv_division}>
                      <td className="px-2 py-1.5">
                        {c.cpv_division} · {c.label}
                      </td>
                      <td className="whitespace-nowrap px-2 py-1.5 text-right tabular-nums">{fmtInt(c.n_contracts)}</td>
                      <td className="whitespace-nowrap px-2 py-1.5 text-right tabular-nums">{fmtEur(c.amount)}</td>
                      <td className="whitespace-nowrap px-2 py-1.5 text-right tabular-nums">
                        {c.hhi == null ? "—" : fmtInt(Math.round(c.hhi))}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          <Card title={`Alertas (${data.alerts.length})`}>
            <AlertsTable alerts={data.alerts} hideBuyer />
          </Card>
          <Card title="Últimos contratos">
            <ContractsTable contracts={data.contracts} side="buyer" procedures={meta.procedure} />
          </Card>
        </>
      )}
    </div>
  );
}
