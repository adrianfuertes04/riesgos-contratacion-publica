import { useMemo } from "react";
import { Link } from "react-router-dom";

import { enc, type BuyerSummary, type CompanySummary, type CpvDivision, type Kpis, type MonthlyPoint } from "../api";
import EChart, { type EChartsOption } from "../components/EChart";
import { Card, Disclaimer, Kpi, RiskBadge, Status } from "../components/ui";
import { fmtDate, fmtEur, fmtEurShort, fmtInt, fmtPct } from "../format";
import { useApi } from "../hooks";

export default function HomePage() {
  const kpis = useApi<Kpis>("/kpis");
  const monthly = useApi<MonthlyPoint[]>("/monthly");
  const cpv = useApi<CpvDivision[]>("/cpv", { limit: 10 });
  const buyers = useApi<BuyerSummary[]>("/buyers", { limit: 10 });
  const companies = useApi<CompanySummary[]>("/companies", { limit: 10 });

  const monthlyOption = useMemo<EChartsOption>(() => {
    const rows = monthly.data ?? [];
    return {
      tooltip: { trigger: "axis", confine: true },
      legend: { top: 0 },
      grid: { left: 60, right: 60, top: 40, bottom: 30 },
      xAxis: { type: "category", data: rows.map((r) => r.month.slice(0, 7)) },
      yAxis: [
        { type: "value", name: "Contratos" },
        { type: "value", name: "Importe", axisLabel: { formatter: (v: number) => fmtEurShort(v) } },
      ],
      series: [
        { name: "Contratos", type: "bar", data: rows.map((r) => r.n_contracts), itemStyle: { color: "#0ea5e9" } },
        {
          name: "Importe adjudicado",
          type: "line",
          yAxisIndex: 1,
          data: rows.map((r) => r.amount),
          itemStyle: { color: "#334155" },
          tooltip: { valueFormatter: (v) => fmtEur(v as number) },
        },
      ],
    };
  }, [monthly.data]);

  const cpvOption = useMemo<EChartsOption>(() => {
    const rows = [...(cpv.data ?? [])].reverse();
    return {
      tooltip: { trigger: "axis", confine: true, valueFormatter: (v) => fmtEur(v as number) },
      grid: { left: 220, right: 30, top: 10, bottom: 30 },
      xAxis: { type: "value", axisLabel: { formatter: (v: number) => fmtEurShort(v) } },
      yAxis: {
        type: "category",
        data: rows.map((r) => `${r.cpv_division} · ${(r.label ?? "").replace(/\.$/, "").slice(0, 32)}`),
      },
      series: [{ type: "bar", data: rows.map((r) => r.amount), itemStyle: { color: "#6366f1" } }],
    };
  }, [cpv.data]);

  const k = kpis.data;
  return (
    <div className="space-y-6">
      <Disclaimer />
      <Status loading={kpis.loading} error={kpis.error} />
      {k && (
        <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-6">
          <Kpi label="Contratos adjudicados" value={fmtInt(k.n_contracts)} />
          <Kpi label="Importe adjudicado" value={fmtEurShort(k.amount)} hint="Sin IVA" />
          <Kpi label="Único licitador" value={fmtPct(k.single_bidder_rate)} hint="En procedimientos abiertos" />
          <Kpi label="Alertas" value={fmtInt(k.n_alerts)} />
          <Kpi label="Órganos / empresas" value={`${fmtInt(k.n_buyers)} / ${fmtInt(k.n_companies)}`} />
          <Kpi label="Periodo" value={k.date_to ? k.date_to.slice(0, 4) : "—"} hint={`${fmtDate(k.date_from)} – ${fmtDate(k.date_to)}`} />
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Evolución mensual">
          <Status loading={monthly.loading} error={monthly.error} />
          {monthly.data && <EChart option={monthlyOption} />}
        </Card>
        <Card title="Principales sectores (división CPV) por importe">
          <Status loading={cpv.loading} error={cpv.error} />
          {cpv.data && <EChart option={cpvOption} />}
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Órganos con mayor importe adjudicado">
          <Status loading={buyers.loading} error={buyers.error} />
          <ul className="divide-y divide-slate-100 text-sm">
            {buyers.data?.map((b) => (
              <li key={b.buyer_id} className="flex items-center justify-between gap-3 py-2">
                <Link className="text-sky-700 hover:underline" to={`/organismos/${enc(b.buyer_id)}`}>
                  {b.name}
                </Link>
                <span className="flex items-center gap-3 whitespace-nowrap tabular-nums">
                  {fmtEur(b.amount)} <RiskBadge score={b.risk_score} />
                </span>
              </li>
            ))}
          </ul>
        </Card>
        <Card title="Empresas con mayor importe adjudicado">
          <Status loading={companies.loading} error={companies.error} />
          <ul className="divide-y divide-slate-100 text-sm">
            {companies.data?.map((c) => (
              <li key={c.company_id} className="flex items-center justify-between gap-3 py-2">
                <Link className="text-sky-700 hover:underline" to={`/empresas/${enc(c.company_id)}`}>
                  {c.name}
                </Link>
                <span className="flex items-center gap-3 whitespace-nowrap tabular-nums">
                  {fmtEur(c.amount)} <RiskBadge score={c.risk_score} />
                </span>
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </div>
  );
}
