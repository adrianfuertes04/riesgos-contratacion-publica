// Cliente tipado de la API (ver api/models.py).

export interface Kpis {
  n_contracts: number;
  amount: number | null;
  single_bidder_rate: number | null;
  n_alerts: number;
  n_buyers: number;
  n_companies: number;
  date_from: string | null;
  date_to: string | null;
}

export interface MonthlyPoint {
  month: string;
  n_contracts: number;
  amount: number | null;
  single_bidder_rate: number | null;
  n_alerts: number | null;
}

export interface CpvDivision {
  cpv_division: string;
  label: string | null;
  n_contracts: number;
  amount: number | null;
  single_bidder_rate: number | null;
}

export interface BuyerSummary {
  buyer_id: string;
  name: string | null;
  nif: string | null;
  type_code: string | null;
  city: string | null;
  nuts2: string | null;
  nuts3: string | null;
  n_contracts: number;
  amount: number | null;
  n_companies: number;
  single_bidder_rate: number | null;
  hhi: number | null;
  risk_score: number | null;
}

export interface BuyerDetail extends BuyerSummary {
  postal_code: string | null;
  hierarchy: string | null;
  n_open: number;
  n_minor: number;
  splitting_rate: number | null;
  non_competitive_rate: number | null;
  short_deadline_rate: number | null;
  price_rate: number | null;
  modified_rate: number | null;
  subjective_share_avg: number | null;
  top_company_share: number | null;
  top_company_id: string | null;
  f_concentration: boolean | null;
  eligible: boolean;
}

export interface CompanySummary {
  company_id: string;
  nif: string | null;
  name: string | null;
  sme: boolean | null;
  n_contracts: number;
  amount: number | null;
  n_buyers: number;
  n_contract_flags: number | null;
  risk_score: number | null;
}

export interface CompanyDetail extends CompanySummary {
  single_bidder_rate: number | null;
  first_date: string | null;
  last_date: string | null;
  nif_valid: boolean;
}

export interface Counterpart {
  id: string;
  name: string | null;
  n_contracts: number;
  amount: number | null;
  share_of_buyer: number | null;
  n_years: number;
  n_flags: number | null;
}

export interface Contract {
  contract_id: string;
  entry_id: string;
  lot_id: string | null;
  title: string | null;
  url: string | null;
  buyer_id: string;
  buyer_name: string | null;
  company_id: string;
  winner_name: string | null;
  procedure_code: string | null;
  contract_type_code: string | null;
  cpv: string | null;
  ref_date: string | null;
  budget: number | null;
  amount: number | null;
  n_offers: number | null;
  risk_score: number | null;
  n_flags: number | null;
}

export interface Alert {
  level: "contrato" | "relacion" | "organismo";
  indicator: string;
  indicator_name: string;
  contract_id: string | null;
  entry_id: string | null;
  url: string | null;
  buyer_id: string;
  buyer_name: string | null;
  company_id: string | null;
  company_name: string | null;
  amount: number | null;
  ref_date: string | null;
  risk_score: number | null;
  explanation: string;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
}

export interface CpvShare {
  cpv_division: string;
  label: string | null;
  n_contracts: number;
  amount: number | null;
  hhi: number | null;
}

export interface BuyerProfile {
  buyer: BuyerDetail;
  companies: Counterpart[];
  cpv: CpvShare[];
  alerts: Alert[];
  contracts: Contract[];
}

export interface CompanyProfile {
  company: CompanyDetail;
  buyers: Counterpart[];
  alerts: Alert[];
  contracts: Contract[];
}

export interface Territory {
  level: number;
  code: string;
  n_contracts: number;
  amount: number | null;
  single_bidder_rate: number | null;
  non_competitive_rate: number | null;
  splitting_rate: number | null;
  risk_score: number | null;
  n_alerts: number | null;
  n_buyers: number;
}

export interface TerritoryProfile {
  territory: Territory;
  buyers: BuyerSummary[];
}

export interface SearchResult {
  kind: "buyer" | "company";
  id: string;
  name: string | null;
  nif: string | null;
  n_contracts: number;
  amount: number | null;
}

export interface GraphNode {
  id: string;
  kind: "buyer" | "company";
  ref: string;
  name: string | null;
  amount: number | null;
  risk_score: number | null;
  n_contracts: number;
}

export interface GraphEdge {
  source: string;
  target: string;
  n_contracts: number;
  amount: number | null;
  n_flags: number;
}

export interface Graph {
  nodes: GraphNode[];
  edges: GraphEdge[];
  truncated: boolean;
}

export interface Meta {
  disclaimer: string;
  indicators: Record<string, string>;
  procedure: Record<string, string>;
  contract_type: Record<string, string>;
  buyer_type: Record<string, string>;
}

type Params = Record<string, string | number | null | undefined>;

export async function get<T>(path: string, params: Params = {}): Promise<T> {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== null && v !== undefined && v !== "") qs.set(k, String(v));
  }
  const url = `/api${path}${qs.size ? `?${qs}` : ""}`;
  const resp = await fetch(url);
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    throw new Error(body.detail ? String(body.detail) : `Error ${resp.status} en ${url}`);
  }
  return resp.json() as Promise<T>;
}

export const enc = encodeURIComponent;
