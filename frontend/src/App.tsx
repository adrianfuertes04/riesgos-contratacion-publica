import { NavLink, Route, Routes, useNavigate } from "react-router-dom";

import { enc } from "./api";
import SearchBox from "./components/SearchBox";
import AlertsPage from "./pages/AlertsPage";
import BuyerPage from "./pages/BuyerPage";
import CompanyPage from "./pages/CompanyPage";
import GraphPage from "./pages/GraphPage";
import HomePage from "./pages/HomePage";
import MapPage from "./pages/MapPage";

const NAV = [
  { to: "/", label: "Inicio" },
  { to: "/mapa", label: "Mapa" },
  { to: "/grafo", label: "Grafo" },
  { to: "/alertas", label: "Alertas" },
];

export default function App() {
  const navigate = useNavigate();
  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-4 px-4 py-3">
          <div className="mr-4">
            <div className="text-base font-semibold">Riesgos en contratación pública</div>
            <div className="text-xs text-slate-500">TFM · datos abiertos PLACSP</div>
          </div>
          <nav className="flex gap-1">
            {NAV.map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                end={n.to === "/"}
                className={({ isActive }) =>
                  `rounded-md px-3 py-1.5 text-sm font-medium ${isActive ? "bg-slate-900 text-white" : "text-slate-700 hover:bg-slate-100"}`
                }
              >
                {n.label}
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto w-full sm:w-80">
            <SearchBox
              onSelect={(r) => navigate(r.kind === "buyer" ? `/organismos/${enc(r.id)}` : `/empresas/${enc(r.id)}`)}
            />
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-6">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/mapa" element={<MapPage />} />
          <Route path="/grafo" element={<GraphPage />} />
          <Route path="/alertas" element={<AlertsPage />} />
          <Route path="/organismos/:id" element={<BuyerPage />} />
          <Route path="/empresas/:id" element={<CompanyPage />} />
          <Route path="*" element={<p className="text-sm text-slate-600">Página no encontrada.</p>} />
        </Routes>
      </main>
    </div>
  );
}
