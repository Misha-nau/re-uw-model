import { ScrollArea, Table as MTable } from "@mantine/core";

import type { Table } from "../api/client";
import { fmtValue } from "../lib/format";
import type { Kind, Scale } from "../lib/format";

/** Financial table: first column labels, then one column per year. Negatives in brackets. */
export function DataTable({ table, scale }: { table: Table; scale: Scale }) {
  return (
    <ScrollArea type="auto">
      <MTable striped highlightOnHover withTableBorder fz="xs" verticalSpacing={4}
        style={{ fontVariantNumeric: "tabular-nums" }}>
        <MTable.Thead>
          <MTable.Tr>
            <MTable.Th style={{ minWidth: 220 }} />
            {table.columns.map((c) => (
              <MTable.Th key={c} ta="right" style={{ whiteSpace: "nowrap" }}>{c}</MTable.Th>
            ))}
          </MTable.Tr>
        </MTable.Thead>
        <MTable.Tbody>
          {table.rows.map((r) => (
            <MTable.Tr key={r.label} fw={r.emphasis ? 700 : undefined}>
              <MTable.Td style={{ whiteSpace: "nowrap" }}>{r.label}</MTable.Td>
              {r.values.map((v, i) => (
                <MTable.Td key={i} ta="right" style={{ whiteSpace: "nowrap" }}>
                  {fmtValue(v, (r.kind ?? "money") as Kind, scale)}
                </MTable.Td>
              ))}
            </MTable.Tr>
          ))}
        </MTable.Tbody>
      </MTable>
    </ScrollArea>
  );
}
