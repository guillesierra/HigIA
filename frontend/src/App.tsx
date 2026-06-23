import { useEffect, useState } from "react";
import { Layout } from "./components/Layout";
import { AlertsPage } from "./pages/AlertsPage";
import { AsturiasPage } from "./pages/AsturiasPage";
import { ConsumptionPage } from "./pages/ConsumptionPage";
import { HomePage } from "./pages/HomePage";
import { MethodologyPage } from "./pages/MethodologyPage";
import { RelationsPage } from "./pages/RelationsPage";
import { SourcesPage } from "./pages/SourcesPage";

const validRoutes = new Set(["home", "sources", "alerts", "consumption", "relations", "asturias", "methodology"]);

export function App() {
  const [route, setRoute] = useState(() => getInitialRoute());

  useEffect(() => {
    const onHash = () => setRoute(getInitialRoute());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  const changeRoute = (next: string) => {
    window.location.hash = next;
    setRoute(next);
  };

  return (
    <Layout activeRoute={route} onRouteChange={changeRoute}>
      {route === "home" && <HomePage onNavigate={changeRoute} />}
      {route === "sources" && <SourcesPage />}
      {route === "alerts" && <AlertsPage />}
      {route === "consumption" && <ConsumptionPage />}
      {route === "relations" && <RelationsPage />}
      {route === "asturias" && <AsturiasPage />}
      {route === "methodology" && <MethodologyPage />}
    </Layout>
  );
}

function getInitialRoute() {
  const hash = window.location.hash.replace("#", "");
  return validRoutes.has(hash) ? hash : "home";
}
