"""Modelos Pydantic de las respuestas de la API."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel


class Page[T](BaseModel):
    items: list[T]
    total: int
    page: int
    size: int


class Kpis(BaseModel):
    n_contracts: int
    amount: float | None
    single_bidder_rate: float | None
    n_alerts: int
    n_buyers: int
    n_companies: int
    date_from: date | None
    date_to: date | None


class MonthlyPoint(BaseModel):
    month: date
    n_contracts: int
    amount: float | None
    single_bidder_rate: float | None
    n_alerts: int | None


class CpvDivision(BaseModel):
    cpv_division: str
    label: str | None
    n_contracts: int
    amount: float | None
    single_bidder_rate: float | None


class BuyerSummary(BaseModel):
    buyer_id: str
    name: str | None
    nif: str | None
    type_code: str | None
    city: str | None
    nuts2: str | None
    nuts3: str | None
    n_contracts: int
    amount: float | None
    n_companies: int
    single_bidder_rate: float | None
    hhi: float | None
    risk_score: float | None


class BuyerDetail(BuyerSummary):
    postal_code: str | None
    hierarchy: str | None
    n_open: int
    n_minor: int
    splitting_rate: float | None
    non_competitive_rate: float | None
    short_deadline_rate: float | None
    price_rate: float | None
    modified_rate: float | None
    subjective_share_avg: float | None
    top_company_share: float | None
    top_company_id: str | None
    f_concentration: bool | None
    eligible: bool


class CompanySummary(BaseModel):
    company_id: str
    nif: str | None
    name: str | None
    sme: bool | None
    n_contracts: int
    amount: float | None
    n_buyers: int
    n_contract_flags: int | None
    risk_score: float | None


class CompanyDetail(CompanySummary):
    single_bidder_rate: float | None
    first_date: date | None
    last_date: date | None
    nif_valid: bool


class Counterpart(BaseModel):
    id: str
    name: str | None
    n_contracts: int
    amount: float | None
    share_of_buyer: float | None
    n_years: int
    n_flags: int | None


class Contract(BaseModel):
    contract_id: str
    entry_id: str
    lot_id: str | None
    title: str | None
    url: str | None
    buyer_id: str
    buyer_name: str | None
    company_id: str
    winner_name: str | None
    procedure_code: str | None
    contract_type_code: str | None
    cpv: str | None
    ref_date: date | None
    budget: float | None
    amount: float | None
    n_offers: int | None
    risk_score: float | None
    n_flags: int | None


class Alert(BaseModel):
    level: Literal["contrato", "relacion", "organismo"]
    indicator: str
    indicator_name: str
    contract_id: str | None
    entry_id: str | None
    url: str | None
    buyer_id: str
    buyer_name: str | None
    company_id: str | None
    company_name: str | None
    amount: float | None
    ref_date: date | None
    risk_score: float | None
    explanation: str


class CpvShare(BaseModel):
    cpv_division: str
    label: str | None
    n_contracts: int
    amount: float | None
    hhi: float | None


class BuyerProfile(BaseModel):
    buyer: BuyerDetail
    companies: list[Counterpart]
    cpv: list[CpvShare]
    alerts: list[Alert]
    contracts: list[Contract]


class CompanyProfile(BaseModel):
    company: CompanyDetail
    buyers: list[Counterpart]
    alerts: list[Alert]
    contracts: list[Contract]


class Territory(BaseModel):
    level: int
    code: str
    n_contracts: int
    amount: float | None
    single_bidder_rate: float | None
    non_competitive_rate: float | None
    splitting_rate: float | None
    risk_score: float | None
    n_alerts: int | None
    n_buyers: int


class TerritoryProfile(BaseModel):
    territory: Territory
    buyers: list[BuyerSummary]


class SearchResult(BaseModel):
    kind: Literal["buyer", "company"]
    id: str
    name: str | None
    nif: str | None
    n_contracts: int
    amount: float | None


class GraphNode(BaseModel):
    id: str
    kind: Literal["buyer", "company"]
    ref: str
    name: str | None
    amount: float | None
    risk_score: float | None
    n_contracts: int


class GraphEdge(BaseModel):
    source: str
    target: str
    n_contracts: int
    amount: float | None
    n_flags: int


class Graph(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    truncated: bool
