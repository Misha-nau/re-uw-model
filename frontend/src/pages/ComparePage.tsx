import { useMemo, useState } from "react";
import { useQueries, useQuery } from "@tanstack/react-query";
import { Alert, Badge, Group, Loader, MultiSelect, Paper, SimpleGrid, Stack, Switch,
  Table as MTable, Text } from "@mantine/core";

import { api } from "../api/client";
import type { Inputs, UnderwriteResponse } from "../api/client";
import { YearBars, YearLines } from "../components/charts";
import { fmtMetric, fmtPct } from "../lib/format";
import { flatten } from "../lib/paths";
import { useScenario } from "../state/ScenarioContext";

const WORKING = "__working__";
const MAX = 6;

interface Col {
  id: string;
  name: string;
  inputs: Inputs | undefined;
  result: UnderwriteResponse | undefined;
  error: unknown;
}

function fmtInputValue(v: unknown): string {
  if (v === null || v === undefined) return "–";
  if (typeof v === "number") {
    if (Math.abs(v) < 1 && v !== 0) return fmtPct(v, 2);
    return v.toLocaleString("en-SG", { maximumFractionDigits: 2 });
  }
  return String(v);
}

export function ComparePage() {
  const s = useScenario();
  const defaultSel = useMemo(() => {
    const ids = s.scenarios.map((x) => x.id);
    return [WORKING, ...ids.filter((id) => id !== s.scenarioId)].slice(0, 3);
  }, [s.scenarios, s.scenarioId]);
  const [selected, setSelected] = useState<string[]>(defaultSel);
  const [diffOnly, setDiffOnly] = useState(true);
  const { data: catalog } = useQuery({ queryKey: ["metrics"], queryFn: api.metrics, staleTime: Infinity });

  const saved = selected.filter((id) => id !== WORKING);
  const inputQs = useQueries({
    queries: saved.map((id) => ({ queryKey: ["scenario", id], queryFn: () => api.getScenario(id) })),
  });
  const inputsById: Record<string, Inputs | undefined> = { [WORKING]: s.inputs ?? undefined };
  saved.forEach((id, i) => { inputsById[id] = inputQs[i].data; });

  const resultQs = useQueries({
    queries: selected.map((id) => ({
      queryKey: ["underwrite", id, inputsById[id]],
      queryFn: () => api.underwrite(inputsById[id] as Inputs),
      enabled: !!inputsById[id],
      staleTime: Infinity,
      retry: false,
    })),
  });

  const cols: Col[] = selected.map((id, i) => ({
    id,
    name: id === WORKING
      ? `${s.inputs?.scenario.name ?? "Working copy"}${s.dirty ? " (unsaved)" : " (current)"}`
      : s.scenarios.find((x) => x.id === id)?.name ?? id,
    inputs: inputsById[id],
    result: resultQs[i]?.data,
    error: resultQs[i]?.error,
  }));
  const ready = cols.filter((c) => c.result);

  const options = [
    { value: WORKING, label: "Current working copy" },
    ...s.scenarios.map((x) => ({ value: x.id, label: x.name })),
  ];

  // input differences
  const flat = cols.map((c) => (c.inputs ? flatten({ ...c.inputs, scenario: undefined }) : {}));
  const keys = Array.from(new Set(flat.flatMap((f) => Object.keys(f)))).sort();
  const diffKeys = keys.filter((k) => new Set(flat.map((f) => JSON.stringify(f[k]))).size > 1);
  const shownKeys = diffOnly ? diffKeys : keys;

  // chart data
  const years = ready[0]?.result?.series.years ?? [];
  const eqData = years.map((y, t) => {
    const row: Record<string, string | number> = { year: y.split(" ")[0] };
    ready.forEach((c, i) => { row[`s${i}`] = c.result!.series.equity_cf[t] ?? 0; });
    return row;
  });
  const noiData = years.slice(1).map((y, t) => {
    const row: Record<string, string | number> = { year: y.split(" ")[0] };
    ready.forEach((c, i) => { row[`s${i}`] = c.result!.series.noi[t] ?? 0; });
    return row;
  });
  const series = ready.map((c, i) => ({ key: `s${i}`, name: c.name }));
  const cur = ready[0]?.result?.currency ?? "SGD";

  return (
    <Stack gap="md">
      <Group align="flex-end" justify="space-between">
        <MultiSelect
          label={`Scenarios to compare (up to ${MAX})`}
          data={options}
          value={selected}
          onChange={(v) => setSelected(v.slice(0, MAX))}
          w={{ base: "100%", md: 720 }}
          searchable
        />
        {resultQs.some((q) => q.isFetching) && <Loader size="sm" />}
      </Group>
      {cols.some((c) => c.error) && (
        <Alert color="red">Some scenarios could not be calculated (invalid inputs).</Alert>
      )}
      {ready.length === 0 ? <Text c="dimmed">Pick at least one scenario.</Text> : (
        <>
          <Paper withBorder p="sm" radius="md">
            <Text fw={600} size="sm" mb="xs">Key metrics (difference vs the first column in grey)</Text>
            <MTable fz="xs" striped withTableBorder verticalSpacing={3}
              style={{ fontVariantNumeric: "tabular-nums" }}>
              <MTable.Thead>
                <MTable.Tr>
                  <MTable.Th>Metric</MTable.Th>
                  {ready.map((c) => <MTable.Th key={c.id} ta="right">{c.name}</MTable.Th>)}
                </MTable.Tr>
              </MTable.Thead>
              <MTable.Tbody>
                {(catalog ?? []).map((m) => {
                  const base = ready[0].result!.metrics[m.key];
                  return (
                    <MTable.Tr key={m.key}>
                      <MTable.Td>{m.label}</MTable.Td>
                      {ready.map((c, i) => {
                        const v = c.result!.metrics[m.key];
                        const d = i > 0 && v != null && base != null ? v - base : null;
                        return (
                          <MTable.Td key={c.id} ta="right">
                            {fmtMetric(v, m.format, cur)}
                            {d !== null && Math.abs(d) > 1e-9 && (
                              <Text span size="10px" c="dimmed" ml={6}>
                                {d > 0 ? "+" : "−"}{fmtMetric(Math.abs(d), m.format, "").trim()}
                              </Text>
                            )}
                          </MTable.Td>
                        );
                      })}
                    </MTable.Tr>
                  );
                })}
              </MTable.Tbody>
            </MTable>
          </Paper>

          <SimpleGrid cols={{ base: 1, lg: 2 }}>
            <Paper withBorder p="sm" radius="md">
              <Text fw={600} size="sm">Equity cash flow, net of fees ({cur})</Text>
              <YearBars data={eqData} series={series} />
            </Paper>
            <Paper withBorder p="sm" radius="md">
              <Text fw={600} size="sm">NOI ({cur})</Text>
              <YearLines data={noiData} series={series} />
            </Paper>
          </SimpleGrid>

          <Paper withBorder p="sm" radius="md">
            <Group justify="space-between" mb="xs">
              <Group gap="xs">
                <Text fw={600} size="sm">Inputs</Text>
                <Badge variant="light">{diffKeys.length} differ</Badge>
              </Group>
              <Switch size="xs" label="Only show differences" checked={diffOnly}
                onChange={(e) => setDiffOnly(e.currentTarget.checked)} />
            </Group>
            <MTable fz="xs" striped withTableBorder verticalSpacing={2}>
              <MTable.Thead>
                <MTable.Tr>
                  <MTable.Th>Input</MTable.Th>
                  {cols.map((c) => <MTable.Th key={c.id} ta="right">{c.name}</MTable.Th>)}
                </MTable.Tr>
              </MTable.Thead>
              <MTable.Tbody>
                {shownKeys.map((k) => (
                  <MTable.Tr key={k}>
                    <MTable.Td ff="monospace">{k}</MTable.Td>
                    {flat.map((f, i) => (
                      <MTable.Td key={i} ta="right"
                        fw={diffKeys.includes(k) ? 600 : undefined}>{fmtInputValue(f[k])}</MTable.Td>
                    ))}
                  </MTable.Tr>
                ))}
              </MTable.Tbody>
            </MTable>
            <Text size="xs" c="dimmed" mt={4}>Rates are shown as %; small decimals are treated as rates.</Text>
          </Paper>
        </>
      )}
    </Stack>
  );
}
