import type { ReactNode } from "react";

type Column<T> = {
  key: string;
  label: string;
  render: (row: T) => ReactNode;
};

export function DataTable<T>({ rows, columns }: { rows: T[]; columns: Column<T>[] }) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column.key}>{column.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={index}>
              {columns.map((column) => (
                <td key={column.key}>{column.render(row)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

