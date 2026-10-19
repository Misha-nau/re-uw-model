import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Alert, Badge, Grid, Group, Loader, Paper, ScrollArea, SegmentedControl, SimpleGrid,
  Stack, Table as MTable, Tabs, Text, Title } from "@mantine/core";

import { api, ApiError } from "../api/client";
import type { UnderwriteResponse } from "../api/client";
import { DataTable } from "../components/DataTable";
import { InputsPanel } from "../components/InputsPanel";
import { KpiStrip } from "../components/KpiStrip";
import { YearBars } from "../components/charts";
import { useUnderwrite } from "../hooks/useUnderwrite";
import { fmtMetric, fmtMoney, fmtPct } from "../lib/format";
import type { Scale } from "../lib/format";
import { useScenario } from "../state/ScenarioContext";

function SourcesUses({ r, scale }: { r: UnderwriteResponse; scale: Scale }) {
  const side = (s: "Uses" | "Sources") => r.sources_uses.filter((x) => x.side === s);
  const total = (s: "Uses" | "Sources") => side(s).reduce((a, x) => a + x.amount, 0);
  const block = (s: "Uses" | "Sources") => (
    <div>
    <MTable fz="xs" withTableBorder verticalSpacing={4} style={{ fontVariantNumeric: "tabular-nums" }}>
      <MTable.Thead>
        <MTable.Tr><MTable.Th>{s}</MTable.Th><MTable.Th ta="right">Amount</MTable.Th>
          <MTable.Th ta="right">%</MTable.Th></MTable.Tr>
      </MTable.Thead>
      <MTable.Tbody>
        {side(s).map((x) => (
          <MTable.Tr key={x.item}>
            <MTable.Td>{x.item}</MTable.Td>
            <MTable.Td ta="right">{fmtMoney(x.amount, scale)}</MTable.Td>
            <MTable.Td ta="right">{fmtPct(x.share, 1)}</MTable.Td>
          </MTable.Tr>
        ))}
        <MTable.Tr fw={700}>
          <MTable.Td>Total</MTable.Td>
          <MTable.Td ta="right">{fmtMoney(total(s), scale)}</MTable.Td>
          <MTable.Td ta="right">100.0%</MTable.Td>
        </MTable.Tr>
      </MTable.Tbody>
    </MTable>
    </div>
  );
  return <SimpleGrid cols={{ base: 1, md: 2 }}>{block("Uses")}{block("Sources")}</SimpleGrid>;
}

const GROUPS = ["Property", "Unlevered", "Equity", "LP / GP", "Debt", "Fees"];

const WF_KPIS = [
  { key: "lp_irr", label: "LP IRR", format: "pct" },
  { key: "lp_multiple", label: "LP multiple", format: "ratio" },
  { key: "gp_irr", label: "GP IRR", format: "pct" },
  { key: "gp_multiple", label: "GP multiple", format: "ratio" },
  { key: "gp_promote", label: "GP promote", format: "money" },
] as const;

function MetricsTable({ r }: { r: UnderwriteResponse }) {
  const { data: catalog } = useQuery({ queryKey: ["metrics"], queryFn: api.metrics, staleTime: Infinity });
  if (!catalog) return null;
  return (
    <SimpleGrid cols={{ base: 1, md: 2, xl: 3 }} spacing="sm">
      {GROUPS.map((g) => (
        <div key={g}>
        <MTable fz="xs" withTableBorder verticalSpacing={3}
          style={{ fontVariantNumeric: "tabular-nums" }}>
          <MTable.Thead><MTable.Tr><MTable.Th colSpan={2}>{g}</MTable.Th></MTable.Tr></MTable.Thead>
          <MTable.Tbody>
            {catalog.filter((m) => m.group === g).map((m) => (
              <MTable.Tr key={m.key}>
                <MTable.Td>{m.label}</MTable.Td>
                <MTable.Td ta="right">{fmtMetric(r.metrics[m.key], m.format, r.currency)}</MTable.Td>
              </MTable.Tr>
            ))}
          </MTable.Tbody>
        </MTable>
        </div>
      ))}
    </SimpleGrid>
  );
}

function Results({ r, scale }: { r: UnderwriteResponse; scale: Scale }) {
  const s = r.series;
  const opData = s.years.slice(1).map((y, i) => ({ year: y, noi: s.noi[i], cfbd: s.cf_before_debt[i] }));
  const eqData = s.years.map((y, i) => ({ year: y, lp: s.lp_cf[i], gp: s.gp_cf[i] }));
  const sizing = r.sizing;
  return (
    <Tabs defaultValue="summary" keepMounted={false}>
      <Tabs.List>
        <Tabs.Tab value="summary">Summary</Tabs.Tab>
        <Tabs.Tab value="operating">Operating cash flow</Tabs.Tab>
        <Tabs.Tab value="components">By component</Tabs.Tab>
        <Tabs.Tab value="returns">Returns</Tabs.Tab>
        <Tabs.Tab value="debt">Debt</Tabs.Tab>
        <Tabs.Tab value="waterfall">Waterfall</Tabs.Tab>
      </Tabs.List>
      <Tabs.Panel value="summary" pt="sm">
        <Stack gap="md">
          <SourcesUses r={r} scale={scale} />
          <MetricsTable r={r} />
        </Stack>
      </Tabs.Panel>
      <Tabs.Panel value="operating" pt="sm">
        <Stack gap="sm">
          <Text size="sm" fw={600}>NOI and cash flow before debt ({r.currency})</Text>
          <YearBars data={opData} series={[{ key: "noi", name: "NOI" },
            { key: "cfbd", name: "CF before debt" }]} />
          <DataTable table={r.operating} scale={scale} />
          <Text size="xs" c="dimmed">The last column is the forward year used only to value the exit.</Text>
        </Stack>
      </Tabs.Panel>
      <Tabs.Panel value="components" pt="sm">
        <Stack gap="md">
          {r.components.map((c) => (
            <div key={c.name}>
              <Text size="sm" fw={600} mb={4}>{c.name}</Text>
              <DataTable table={c.table} scale={scale} />
            </div>
          ))}
        </Stack>
      </Tabs.Panel>
      <Tabs.Panel value="returns" pt="sm">
        <DataTable table={r.cash_flows} scale={scale} />
      </Tabs.Panel>
      <Tabs.Panel value="debt" pt="sm">
        <Stack gap="sm">
          <Group gap="xs">
            <Text size="sm">Loan {fmtMetric(sizing.amount, "money", r.currency)}; binding constraint:</Text>
            <Badge variant="light">{sizing.binding}</Badge>
            <Text size="sm" c="dimmed">
              LTV amount {fmtMetric(sizing.ltv_amount, "money", r.currency)}
              {sizing.dscr_amount != null && `, DSCR amount ${fmtMetric(sizing.dscr_amount, "money", r.currency)}`}
              {sizing.debt_yield_amount != null &&
                `, debt-yield amount ${fmtMetric(sizing.debt_yield_amount, "money", r.currency)}`}
            </Text>
          </Group>
          <DataTable table={r.debt} scale={scale} />
        </Stack>
      </Tabs.Panel>
      <Tabs.Panel value="waterfall" pt="sm">
        <Stack gap="sm">
          <Group gap="xl">
            {WF_KPIS.map((k) => (
              <div key={k.key}>
                <Text size="xs" c="dimmed">{k.label}</Text>
                <Text fw={700}>{fmtMetric(r.metrics[k.key], k.format, r.currency)}</Text>
              </div>
            ))}
          </Group>
          <Text size="sm" fw={600}>LP and GP net cash flow ({r.currency})</Text>
          <YearBars data={eqData} series={[{ key: "lp", name: "LP" }, { key: "gp", name: "GP" }]} />
          <DataTable table={r.waterfall} scale={scale} />
        </Stack>
      </Tabs.Panel>
    </Tabs>
  );
}

export function UnderwritingPage() {
  const { inputs } = useScenario();
  const q = useUnderwrite(inputs);
  const [scale, setScale] = useState<Scale>("m");
  if (!inputs) return <Loader m="xl" />;
  const err = q.error instanceof ApiError ? q.error : null;

  return (
    <Grid gap="md">
      <Grid.Col span={{ base: 12, lg: 4 }}>
        <ScrollArea.Autosize mah="calc(100vh - 130px)" offsetScrollbars>
          <InputsPanel />
        </ScrollArea.Autosize>
      </Grid.Col>
      <Grid.Col span={{ base: 12, lg: 8 }}>
        <ScrollArea.Autosize mah="calc(100vh - 130px)" offsetScrollbars>
          <Stack gap="sm">
            <Group justify="space-between">
              <Group gap="xs">
                <Title order={4}>{inputs.property.name}</Title>
                {q.isFetching && <Loader size="xs" />}
              </Group>
              <SegmentedControl size="xs" value={scale} onChange={(v) => setScale(v as Scale)} data={[
                { value: "m", label: `${inputs.analysis?.currency ?? "SGD"} m` },
                { value: "k", label: "k" }, { value: "1", label: "units" }]} />
            </Group>
            {q.error && (
              <Alert color="red" title={err?.message ?? "Calculation failed"}>
                {err?.details.length ? (
                  <Stack gap={2}>{err.details.map((d) => <Text key={d} size="xs">{d}</Text>)}</Stack>
                ) : String(q.error)}
                <Text size="xs" mt={4} c="dimmed">Showing the last valid result.</Text>
              </Alert>
            )}
            {q.data && (
              <>
                <KpiStrip result={q.data} />
                <Paper withBorder p="sm" radius="md"><Results r={q.data} scale={scale} /></Paper>
              </>
            )}
          </Stack>
        </ScrollArea.Autosize>
      </Grid.Col>
    </Grid>
  );
}
