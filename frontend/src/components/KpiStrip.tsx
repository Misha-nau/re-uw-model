import { Paper, SimpleGrid, Text } from "@mantine/core";

import type { UnderwriteResponse } from "../api/client";
import { fmtMetric } from "../lib/format";

const KPIS: { key: string; label: string; format: "money" | "pct" | "ratio" | "psf" }[] = [
  { key: "levered_irr", label: "Equity IRR (net)", format: "pct" },
  { key: "lp_irr", label: "LP IRR", format: "pct" },
  { key: "unlevered_irr", label: "Unlevered IRR", format: "pct" },
  { key: "levered_multiple", label: "Equity multiple", format: "ratio" },
  { key: "entry_cap_rate", label: "Entry cap rate", format: "pct" },
  { key: "dscr_year1", label: "Year 1 DSCR", format: "ratio" },
  { key: "equity", label: "Equity", format: "money" },
  { key: "exit_value", label: "Exit value", format: "money" },
];

export function KpiStrip({ result }: { result: UnderwriteResponse }) {
  return (
    <SimpleGrid cols={{ base: 2, sm: 4, xl: 8 }} spacing="xs">
      {KPIS.map((k) => (
        <Paper key={k.key} withBorder p="xs" radius="md">
          <Text size="xs" c="dimmed" style={{ whiteSpace: "nowrap" }}>
            {k.label}{k.format === "money" ? ` (${result.currency})` : ""}
          </Text>
          <Text fw={700} size="lg" style={{ whiteSpace: "nowrap" }}>
            {fmtMetric(result.metrics[k.key], k.format, "")}
          </Text>
        </Paper>
      ))}
    </SimpleGrid>
  );
}
