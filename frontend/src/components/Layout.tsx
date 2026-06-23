import { Activity, AlertTriangle, BarChart3, BookOpen, Database, FileText, GitBranch, Home, MapPinned } from "lucide-react";
import type { ReactNode } from "react";

type Route = {
  id: string;
  label: string;
  icon: ReactNode;
};

const routes: Route[] = [
  { id: "home", label: "Home", icon: <Home size={18} /> },
  { id: "sources", label: "Fuentes", icon: <Database size={18} /> },
  { id: "alerts", label: "Alertas", icon: <AlertTriangle size={18} /> },
  { id: "consumption", label: "Consumo", icon: <Activity size={18} /> },
  { id: "relations", label: "Relaciones", icon: <GitBranch size={18} /> },
  { id: "analytics", label: "Analisis", icon: <BarChart3 size={18} /> },
  { id: "asturias", label: "Asturias", icon: <MapPinned size={18} /> },
  { id: "methodology", label: "Metodo", icon: <BookOpen size={18} /> }
];

type LayoutProps = {
  activeRoute: string;
  onRouteChange: (route: string) => void;
  children: ReactNode;
};

export function Layout({ activeRoute, onRouteChange, children }: LayoutProps) {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <FileText size={22} />
          <div>
            <strong>HigIA</strong>
            <span>public pharma data</span>
          </div>
        </div>
        <nav className="nav-list" aria-label="Main navigation">
          {routes.map((route) => (
            <button
              key={route.id}
              type="button"
              className={route.id === activeRoute ? "nav-item active" : "nav-item"}
              onClick={() => onRouteChange(route.id)}
              title={route.label}
            >
              {route.icon}
              <span>{route.label}</span>
            </button>
          ))}
        </nav>
      </aside>
      <main className="content">{children}</main>
    </div>
  );
}

