import { Link, useParams } from "react-router-dom";

import { enc, type CompanyProfile } from "../api";
import { AlertsTable, ContractsTable, CounterpartsTable } from "../components/tables";
import { Card, Disclaimer, Kpi, RiskBadge, Status } from "../components/ui";
import { fmtDate, fmtEurShort, fmtInt, fmtPct } from "../format";
import { useApi } from "../hooks";
import { useMeta } from "../meta";

export default function CompanyPage() {
  const { id = "" } = useParams();
  const meta = useMeta();
  const { data, loading, error } = useApi<CompanyProfile>(`/companies/${enc(id)}`);
  const c = data?.company;

  return (
    <div className="space-y-6">
      <Status loading={loading} error={error} />
      {c && data && (
        <>
          <div>
            <div className="text-xs uppercase tracking-wide text-slate-500">Empresa adjudicataria</div>
            <h1 className="text-xl font-semibold">{c.name}</h1>
            <div className="mt-1 text-sm text-slate-600">
              NIF {c.nif ?? "—"}{" "}
              {c.nif && (
                <span className={c.nif_valid ? "text-emerald-700" : "text-amber-700"}>
                  ({c.nif_valid ? "formato válido" : "formato no verificable"})
                </span>
              )}
              {c.sme != null && ` · ${c.sme ? "PYME" : "No PYME"}`} · Actividad entre {fmtDate(c.first_date)} y{" "}
              {fmtDate(c.last_date)}
            </div>
            <Link className="mt-2 inline-block text-sm text-sky-700 hover:underline" to={`/grafo?node=company:${enc(c.company_id)}`}>
              Ver en el explorador de grafo →
            </Link>
          </div>
          <Disclaimer />
          <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
            <Kpi label="Contratos" value={fmtInt(c.n_contracts)} />
            <Kpi label="Importe" value={fmtEurShort(c.amount)} />
            <Kpi label="Órganos distintos" value={fmtInt(c.n_buyers)} />
            <Kpi label="Único licitador" value={fmtPct(c.single_bidder_rate)} hint="En sus contratos abiertos" />
            <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
              <div className="text-xs font-medium uppercase tracking-wide text-slate-500">Riesgo medio por contrato</div>
              <div className="mt-2">
                <RiskBadge score={c.risk_score} />
              </div>
              <div className="mt-1 text-xs text-slate-500">{fmtInt(c.n_contract_flags)} señales en sus contratos</div>
            </div>
          </div>
          <Card title="Órganos contratantes">
            <CounterpartsTable rows={data.buyers} kind="buyer" />
          </Card>
          <Card title={`Alertas (${data.alerts.length})`}>
            <AlertsTable alerts={data.alerts} />
          </Card>
          <Card title="Últimos contratos">
            <ContractsTable contracts={data.contracts} side="company" procedures={meta.procedure} />
          </Card>
          <p className="text-xs text-slate-400">
            Administradores y vínculos societarios (BORME) se incorporarán en la capa 2 del proyecto.
          </p>
        </>
      )}
    </div>
  );
}
