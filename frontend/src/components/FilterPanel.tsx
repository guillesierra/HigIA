import type { ReactNode } from "react";

type FilterPanelProps = {
  children: ReactNode;
  actions?: ReactNode;
};

export function FilterPanel({ children, actions }: FilterPanelProps) {
  return (
    <section className="filter-panel" aria-label="Filters">
      <div className="filter-controls">{children}</div>
      {actions ? <div className="filter-actions">{actions}</div> : null}
    </section>
  );
}

