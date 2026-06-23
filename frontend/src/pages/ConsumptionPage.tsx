import { Download } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { RankingChart } from "../charts/RankingChart";
import { ConsumptionChart } from "../components/ConsumptionChart";
import { ConsumptionTable } from "../components/ConsumptionTable";
import { FilterPanel } from "../components/FilterPanel";
import { LoadingState } from "../components/Status";
import { api } from "../services/api";
import type { ConsumptionRecord } from "../types/domain";

export function ConsumptionPage() {
  const [records, setRecords] = useState<ConsumptionRecord[]>([]);
  const [year, setYear] = useState("");
  const [geography, setGeography] = useState("");
  const [atc, setAtc] = useState("");
  const [medicine, setMedicine] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.consumption().then(setRecords).finally(() => setLoading(false));
  }, []);

  const filtered = useMemo(
    () =>
      records.filter((record) => {
        const rowText = `${record.atc_code ?? ""} ${record.category ?? ""} ${record.drug_name ?? ""} ${record.active_ingredient ?? ""}`.toLowerCase();
        if (year && record.year !== Number(year)) return false;
        if (geography && !record.geography.toLowerCase().includes(geography.toLowerCase())) return false;
        if (atc && !(record.atc_code ?? record.category ?? "").toLowerCase().startsWith(atc.toLowerCase())) return false;
        if (medicine && !rowText.includes(medicine.toLowerCase())) return false;
        return true;
      }),
    [records, year, geography, atc, medicine]
  );

  if (loading) return <LoadingState />;

  const csv = makeCsv(filtered);

  return (
    <div className="page">
      <header className="page-header compact">
        <div>
          <p className="eyebrow">Aggregated metrics</p>
          <h1>Consumo</h1>
        </div>
        <a className="download-link" href={`data:text/csv;charset=utf-8,${encodeURIComponent(csv)}`} download="higia-consumo.csv">
          <Download size={16} />
          CSV
        </a>
      </header>

      <FilterPanel>
        <input value={year} onChange={(event) => setYear(event.target.value)} placeholder="Ano" inputMode="numeric" />
        <input value={geography} onChange={(event) => setGeography(event.target.value)} placeholder="Geografia" />
        <input value={atc} onChange={(event) => setAtc(event.target.value)} placeholder="ATC o categoria" />
        <input value={medicine} onChange={(event) => setMedicine(event.target.value)} placeholder="Medicamento" />
      </FilterPanel>

      <section className="grid two">
        <div className="panel">
          <div className="panel-heading">
            <h2>Evolucion anual</h2>
          </div>
          <ConsumptionChart records={filtered} />
        </div>
        <div className="panel">
          <div className="panel-heading">
            <h2>Ranking por DHD</h2>
          </div>
          <RankingChart records={filtered} />
        </div>
      </section>

      <ConsumptionTable records={filtered} />
    </div>
  );
}

function makeCsv(rows: ConsumptionRecord[]) {
  const header = ["year", "geography", "sector", "atc_code", "category", "drug_name", "active_ingredient", "dhd", "packages"];
  const lines = rows.map((row) =>
    header
      .map((key) => {
        const value = row[key as keyof ConsumptionRecord] ?? "";
        return `"${String(value).replace(/"/g, '""')}"`;
      })
      .join(",")
  );
  return [header.join(","), ...lines].join("\n");
}

