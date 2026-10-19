import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Alert, Box, Button, Group, Loader, NumberInput, Paper, Select, SimpleGrid, Stack,
  Table as MTable, Text } from "@mantine/core";

import { api } from "../api/client";
import type { MetricInfo, ParameterInfo } from "../api/client";
import { TornadoChart, divergingColor, usePalette } from "../components/charts";
import { fmtInput, fmtMetric } from "../lib/format";
import { useInputs } from "../state/ScenarioContext";

function stepScale(p?: ParameterInfo) {
  return p?.unit === "pct" ? 100 : 1;
}

function StepInput({ p, value, onChange }: {
  p?: ParameterInfo; value: number | undefined; onChange: (v: number) => void;
}) {
  const k = stepScale(p);
  return (
    <NumberInput size="xs" label="Step" w={110} decimalScale={4}
      suffix={p?.unit === "pct" ? "%" : undefined}
      value={value === undefined ? "" : Number((value * k).toFixed(6))}
      onChange={(v) => typeof v === "number" && onChange(v / k)} />
  );
}

export function SensitivityPage() {
  const inputs = useInputs();
  const c = usePalette();
  const params = useQuery({
    queryKey: ["params", inputs.components.map((x) => x.name), inputs],
    queryFn: () => api.parameters(inputs),
    staleTime: Infinity,
  });
  const { data: catalog } = useQuery({ queryKey: ["metrics"], queryFn: api.metrics, staleTime: Infinity });

  const [x, setX] = useState("exit_cap");
  const [y, setY] = useState("c0_growth");
  const [metric, setMetric] = useState("levered_irr");
  const [steps, setSteps] = useState(2);
  const [xStep, setXStep] = useState<number>();
  const [yStep, setYStep] = useState<number>();
  const [tMetric, setTMetric] = useState("levered_irr");

  const byKey = useMemo(() => Object.fromEntries((params.data ?? []).map((p) => [p.key, p])),
    [params.data]);
  useEffect(() => { setXStep(byKey[x]?.step); }, [x, byKey]);
  useEffect(() => { setYStep(byKey[y]?.step); }, [y, byKey]);

  const values = (p: ParameterInfo | undefined, step: number | undefined) =>
    p && step !== undefined
      ? Array.from({ length: 2 * steps + 1 }, (_, i) => p.base + (i - steps) * step) : undefined;

  const grid = useMutation({
    mutationFn: () => api.sensitivity({
      inputs, x, y, metric, steps,
      x_values: values(byKey[x], xStep), y_values: values(byKey[y], yStep),
    }),
  });
  const torn = useMutation({ mutationFn: () => api.tornado({ inputs, metric: tMetric }) });

  // run once parameters are known, and whenever the working inputs change
  useEffect(() => {
    if (params.data) { grid.mutate(); torn.mutate(); }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.data]);

  const paramOptions = (params.data ?? []).map((p) => ({ value: p.key, label: p.label }));
  const metricOptions = (catalog ?? []).map((m) => ({ value: m.key, label: m.label, group: m.group }));
  const grouped = Object.entries(metricOptions.reduce<Record<string, { value: string; label: string }[]>>(
    (acc, m) => { (acc[m.group] ??= []).push({ value: m.value, label: m.label }); return acc; }, {}))
    .map(([group, items]) => ({ group, items }));
  const info = (k: string): MetricInfo | undefined => catalog?.find((m) => m.key === k);
  const fmtM = (v: number | null | undefined, k: string) =>
    fmtMetric(v, info(k)?.format ?? "pct", inputs.analysis?.currency ?? "SGD");

  const g = grid.data;
  const deltas = g ? g.values.flat().filter((v): v is number => v !== null).map((v) => v - (g.base ?? 0)) : [];
  const maxAbs = deltas.length ? Math.max(...deltas.map(Math.abs)) : 0;
  const tFmt = (v: number) => {
    const f = info(tMetric)?.format ?? "pct";
    if (f === "pct") return `${v >= 0 ? "+" : ""}${(v * 100).toFixed(2)}pp`;
    if (f === "ratio") return `${v >= 0 ? "+" : ""}${v.toFixed(2)}x`;
    return `${v >= 0 ? "+" : ""}${(v / 1e6).toFixed(1)}m`;
  };
  const t = torn.data;
  const tData = (t?.bars ?? []).map((b) => ({
    label: b.label,
    low: b.low === null || t?.base == null ? null : b.low - t.base,
    high: b.high === null || t?.base == null ? null : b.high - t.base,
    lowLabel: fmtInput(b.low_input, b.unit),
    highLabel: fmtInput(b.high_input, b.unit),
  }));

  if (params.isLoading) return <Loader />;

  return (
    <SimpleGrid cols={{ base: 1, xl: 2 }} spacing="md">
      <Paper withBorder p="sm" radius="md">
        <Stack gap="sm">
          <Text fw={600}>Two-way sensitivity</Text>
          <Group gap="xs" align="flex-end">
            <Select size="xs" label="Columns (X)" data={paramOptions} value={x} w={200}
              onChange={(v) => v && setX(v)} allowDeselect={false} />
            <StepInput p={byKey[x]} value={xStep} onChange={setXStep} />
            <Select size="xs" label="Rows (Y)" data={paramOptions} value={y} w={200}
              onChange={(v) => v && setY(v)} allowDeselect={false} />
            <StepInput p={byKey[y]} value={yStep} onChange={setYStep} />
          </Group>
          <Group gap="xs" align="flex-end">
            <Select size="xs" label="Output" data={grouped} value={metric} w={260}
              onChange={(v) => v && setMetric(v)} allowDeselect={false} />
            <NumberInput size="xs" label="Steps each side" min={1} max={5} w={110} value={steps}
              onChange={(v) => typeof v === "number" && setSteps(v)} />
            <Button size="xs" onClick={() => grid.mutate()} loading={grid.isPending}>Run</Button>
          </Group>
          {grid.error && <Alert color="red">{String(grid.error)}</Alert>}
          {g && (
            <>
              <Box style={{ overflowX: "auto" }}>
                <MTable fz="xs" withTableBorder withColumnBorders verticalSpacing={6}
                  style={{ fontVariantNumeric: "tabular-nums" }}>
                  <MTable.Thead>
                    <MTable.Tr>
                      <MTable.Th>{g.y.label} ↓ / {g.x.label} →</MTable.Th>
                      {g.x_values.map((xv, j) => (
                        <MTable.Th key={j} ta="center">{fmtInput(xv, g.x.unit)}</MTable.Th>
                      ))}
                    </MTable.Tr>
                  </MTable.Thead>
                  <MTable.Tbody>
                    {g.values.map((row, i) => (
                      <MTable.Tr key={i}>
                        <MTable.Th>{fmtInput(g.y_values[i], g.y.unit)}</MTable.Th>
                        {row.map((v, j) => {
                          const isBase = Math.abs(g.x_values[j] - g.x.base) < 1e-9
                            && Math.abs(g.y_values[i] - g.y.base) < 1e-9;
                          return (
                            <MTable.Td key={j} ta="center" title={v === null ? "Invalid inputs" : undefined}
                              style={{
                                background: v === null ? undefined
                                  : divergingColor(v - (g.base ?? 0), maxAbs, c),
                                outline: isBase ? `2px solid ${c.text}` : undefined,
                                outlineOffset: -2,
                                fontWeight: isBase ? 700 : undefined,
                                color: "#0b0b0b",
                              }}>
                              {v === null ? "n/a" : fmtM(v, metric)}
                            </MTable.Td>
                          );
                        })}
                      </MTable.Tr>
                    ))}
                  </MTable.Tbody>
                </MTable>
              </Box>
              <Text size="xs" c="dimmed">
                Outlined cell = current inputs ({fmtM(g.base, metric)}). Blue = better than base,
                red = worse, grey = about the same. Each cell re-runs the full model.
              </Text>
            </>
          )}
        </Stack>
      </Paper>

      <Paper withBorder p="sm" radius="md">
        <Stack gap="sm">
          <Text fw={600}>Tornado: what moves the result most</Text>
          <Group gap="xs" align="flex-end">
            <Select size="xs" label="Output" data={grouped} value={tMetric} w={260}
              onChange={(v) => v && setTMetric(v)} allowDeselect={false} />
            <Button size="xs" onClick={() => torn.mutate()} loading={torn.isPending}>Run</Button>
          </Group>
          {t && (
            <>
              <Text size="xs" c="dimmed">
                Change vs base ({fmtM(t.base, t.metric)}) when each input moves one step down
                (orange) or up (blue). Step sizes match the two-way table defaults.
              </Text>
              <TornadoChart data={tData} fmt={tFmt} />
            </>
          )}
        </Stack>
      </Paper>
    </SimpleGrid>
  );
}
