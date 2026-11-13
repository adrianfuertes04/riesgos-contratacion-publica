import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { enc, type Territory, type TerritoryProfile } from "../api";
import EChart, { echarts, type ECElementEvent, type EChartsOption } from "../components/EChart";
import { Card, Disclaimer, Empty, RiskBadge, Status } from "../components/ui";
import { fmtEur, fmtEurShort, fmtInt, fmtPct, fmtScore } from "../format";
import { useApi } from "../hooks";

type Metric = keyof Pick<
  Territory,
  "n_contracts" | "amount" | "single_bidder_rate" | "non_competitive_rate" | "risk_score" | "n_alerts"
>;

const METRICS: { key: Metric; label: string; fmt: (v: number | null) => string }[] = [
  { key: "risk_score", label: "Riesgo medio por contrato (0-100)", fmt: fmtScore },
  { key: "single_bidder_rate", label: "% único licitador", fmt: (v) => fmtPct(v) },
  { key: "non_competitive_rate", label: "% procedimientos poco competitivos", fmt: (v) => fmtPct(v) },
  { key: "n_alerts", label: "Nº de alertas", fmt: fmtInt },
  { key: "n_contracts", label: "Nº de contratos", fmt: fmtInt },
  { key: "amount", label: "Importe adjudicado", fmt: fmtEurShort },
];

interface GeoFeature {
  properties: { code: string; name: string };
}

export default function MapPage() {
  const [level, setLevel] = useState<2 | 3>(2);
  const [metric, setMetric] = useState<Metric>("risk_score");
  const [selected, setSelected] = useState<string | null>(null);
  const [names, setNames] = useState<Record<string, string>>({});
  const [geoReady, setGeoReady] = useState<number | null>(null);
  const [geoError, setGeoError] = useState<string | null>(null);
  const territories = useApi<Territory[]>("/territories", { level });
  const profile = useApi<TerritoryProfile>(selected ? `/territories/${enc(selected)}` : null);

  // Geometrías NUTS de Eurostat/GISCO (generadas con pipelines/reference/build_geo.py).
  useEffect(() => {
    const mapName = `nuts${level}`;
    let cancelled = false;
    setGeoReady(null);
    setGeoError(null);
    fetch(`/geo/${mapName}.json`)
      .then((r) => {
        if (!r.ok) throw new Error(`Error ${r.status} cargando el mapa ${mapName}`);
        return r.json();
      })
      .then((geo: { features: GeoFeature[] }) => {
        if (cancelled) return;
        echarts.registerMap(mapName, geo as never);
        setNames(Object.fromEntries(geo.features.map((f) => [f.properties.code, f.properties.name])));
        setGeoReady(level);
      })
      .catch((err: unknown) => {
        if (!cancelled) setGeoError(err instanceof Error ? err.message : "No se pudo cargar la geometría del mapa");
      });
    return () => {
      cancelled = true;
    };
  }, [level]);

  const def = METRICS.find((m) => m.key === metric)!;
  const option = useMemo<EChartsOption>(() => {
    const rows = territories.data ?? [];
    const values = rows.map((r) => r[metric]).filter((v): v is number => v != null);
    return {
      tooltip: {
        trigger: "item",
        confine: true,
        formatter: (p) => {
          const item = p as unknown as { name: string; value: number };
          const label = names[item.name] ?? item.name;
          return `${label} (${item.name})<br/>${def.label}: <b>${Number.isFinite(item.value) ? def.fmt(item.value) : "sin datos"}</b>`;
        },
      },
      visualMap: {
        min: values.length ? Math.min(...values) : 0,
        max: values.length ? Math.max(...values) : 1,
        right: 10,
        bottom: 10,
        calculable: true,
        inRange: { color: ["#ecfeff", "#38bdf8", "#1e3a8a"] },
        formatter: (v) => def.fmt(Number(v)),
      },
      series: [
        {
          type: "map",
          map: `nuts${level}`,
          nameProperty: "code",
          roam: true,
          top: 20,
          bottom: 20,
          left: 20,
          right: 90,
          emphasis: { label: { show: false }, itemStyle: { areaColor: "#fbbf24" } },
          select: { disabled: true },
          itemStyle: { borderColor: "#94a3b8", areaColor: "#f1f5f9" },
          data: rows.map((r) => ({ name: r.code, value: r[metric] ?? undefined })),
        },
      ],
    };
  }, [territories.data, metric, level, names, def]);

  const onClick = useCallback((p: ECElementEvent) => setSelected(p.name), []);
  const t = profile.data?.territory;

  return (
    <div className="space-y-4">
      <Disclaimer />
      <div className="flex flex-wrap items-center gap-3">
        <label className="text-sm">
          Nivel{" "}
          <select
            className="ml-1 rounded border border-slate-300 px-2 py-1"
            value={level}
            onChange={(e) => {
              setLevel(Number(e.target.value) as 2 | 3);
              setSelected(null);
            }}
          >
            <option value={2}>Comunidad autónoma (NUTS 2)</option>
            <option value={3}>Provincia (NUTS 3)</option>
          </select>
        </label>
        <label className="text-sm">
          Indicador{" "}
          <select
            className="ml-1 rounded border border-slate-300 px-2 py-1"
            value={metric}
            onChange={(e) => setMetric(e.target.value as Metric)}
          >
            {METRICS.map((m) => (
              <option key={m.key} value={m.key}>
                {m.label}
              </option>
            ))}
          </select>
        </label>
        <span className="text-xs text-slate-500">Territorio = lugar de ejecución declarado (NUTS). Canarias desplazada.</span>
      </div>
      <div className="grid gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <Card>
            <Status loading={!geoError && (territories.loading || geoReady !== level)} error={geoError ?? territories.error} />
            {territories.data && geoReady === level && <EChart option={option} height={560} onClick={onClick} />}
          </Card>
        </div>
        <Card
          title={selected ? `${names[selected] ?? selected} (${selected})` : "Ficha del territorio"}
          actions={
            selected && (
              <button
                type="button"
                className="rounded border border-slate-300 px-2 py-0.5 text-xs text-slate-600 hover:bg-slate-50"
                onClick={() => setSelected(null)}
              >
                Limpiar
              </button>
            )
          }
        >
          {!selected && <Empty>Pulsa una región del mapa.</Empty>}
          <Status loading={profile.loading} error={profile.error} />
          {t && (
            <div className="space-y-4 text-sm">
              <dl className="grid grid-cols-2 gap-2">
                <dt className="text-slate-500">Contratos</dt>
                <dd className="text-right tabular-nums">{fmtInt(t.n_contracts)}</dd>
                <dt className="text-slate-500">Importe</dt>
                <dd className="text-right tabular-nums">{fmtEur(t.amount)}</dd>
                <dt className="text-slate-500">Único licitador</dt>
                <dd className="text-right tabular-nums">{fmtPct(t.single_bidder_rate)}</dd>
                <dt className="text-slate-500">Poco competitivos</dt>
                <dd className="text-right tabular-nums">{fmtPct(t.non_competitive_rate)}</dd>
                <dt className="text-slate-500">Alertas</dt>
                <dd className="text-right tabular-nums">{fmtInt(t.n_alerts)}</dd>
                <dt className="text-slate-500">Riesgo medio</dt>
                <dd className="text-right">
                  <RiskBadge score={t.risk_score} />
                </dd>
              </dl>
              <div>
                <h3 className="mb-1 text-xs font-semibold uppercase text-slate-500">Órganos principales</h3>
                <ul className="divide-y divide-slate-100">
                  {profile.data?.buyers.map((b) => (
                    <li key={b.buyer_id} className="flex justify-between gap-2 py-1.5">
                      <Link className="text-sky-700 hover:underline" to={`/organismos/${enc(b.buyer_id)}`}>
                        {b.name}
                      </Link>
                      <span className="whitespace-nowrap tabular-nums">{fmtEurShort(b.amount)}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
