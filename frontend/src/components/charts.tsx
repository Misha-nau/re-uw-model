import { useComputedColorScheme } from "@mantine/core";
import {
  Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer,
  Tooltip, XAxis, YAxis,
} from "recharts";

/* Reference palette (dataviz skill): fixed categorical order, recessive chrome. */
const PALETTE = {
  light: {
    series: ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"],
    grid: "#e1e0d9", axis: "#c3c2b7", muted: "#898781", text: "#52514e", surface: "#fcfcfb",
    pos: "#2a78d6", neg: "#e34948", mid: "#f0efec",
  },
  dark: {
    series: ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300", "#9085e9", "#e66767"],
    grid: "#2c2c2a", axis: "#383835", muted: "#898781", text: "#c3c2b7", surface: "#1a1a19",
    pos: "#3987e5", neg: "#e66767", mid: "#383835",
  },
};

export function usePalette() {
  const scheme = useComputedColorScheme("light");
  return PALETTE[scheme];
}

const axisProps = (c: typeof PALETTE.light) => ({
  tick: { fontSize: 11, fill: c.muted },
  axisLine: { stroke: c.axis },
  tickLine: false,
});

const m = (v: number) => (v / 1e6).toLocaleString("en-SG", { maximumFractionDigits: 1 });

export interface SeriesDef {
  key: string;
  name: string;
}

/** Grouped bars by year (one bar per series). Values in currency units, shown in millions. */
export function YearBars({ data, series, height = 240, unit = "m" }: {
  data: Record<string, number | string>[];
  series: SeriesDef[];
  height?: number;
  unit?: string;
}) {
  const c = usePalette();
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} barGap={2} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid vertical={false} stroke={c.grid} />
        <XAxis dataKey="year" {...axisProps(c)} />
        <YAxis {...axisProps(c)} width={56} tickFormatter={(v: number) => m(v)} unit={unit} />
        <ReferenceLine y={0} stroke={c.axis} />
        <Tooltip
          cursor={{ fill: c.grid, opacity: 0.4 }}
          formatter={(v) => `${m(Number(v))}${unit}`}
          contentStyle={{ background: c.surface, border: `1px solid ${c.axis}`, fontSize: 12 }}
          labelStyle={{ color: c.text }}
        />
        {series.length > 1 && <Legend wrapperStyle={{ fontSize: 12, color: c.text }} />}
        {series.map((s, i) => (
          <Bar key={s.key} dataKey={s.key} name={s.name} fill={c.series[i % 8]} radius={[4, 4, 0, 0]}
            maxBarSize={36} />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}

/** Lines by year (one line per series). */
export function YearLines({ data, series, height = 240, unit = "m" }: {
  data: Record<string, number | string>[];
  series: SeriesDef[];
  height?: number;
  unit?: string;
}) {
  const c = usePalette();
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
        <CartesianGrid vertical={false} stroke={c.grid} />
        <XAxis dataKey="year" {...axisProps(c)} />
        <YAxis {...axisProps(c)} width={56} tickFormatter={(v: number) => m(v)} unit={unit}
          domain={["auto", "auto"]} />
        <Tooltip
          formatter={(v) => `${m(Number(v))}${unit}`}
          contentStyle={{ background: c.surface, border: `1px solid ${c.axis}`, fontSize: 12 }}
          labelStyle={{ color: c.text }}
        />
        {series.length > 1 && <Legend wrapperStyle={{ fontSize: 12, color: c.text }} />}
        {series.map((s, i) => (
          <Line key={s.key} dataKey={s.key} name={s.name} stroke={c.series[i % 8]} strokeWidth={2}
            dot={{ r: 4, strokeWidth: 2, stroke: c.surface }} activeDot={{ r: 5 }} />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}

export interface TornadoDatum {
  label: string;
  low: number | null; // metric change vs base when the input moves down
  high: number | null;
  lowLabel: string;
  highLabel: string;
}

/** Tornado: change in the metric vs base, for a low and a high move in each input. */
export function TornadoChart({ data, fmt }: {
  data: TornadoDatum[];
  fmt: (v: number) => string;
}) {
  const c = usePalette();
  const height = Math.max(160, data.length * 34 + 60);
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} layout="vertical" barGap={2} margin={{ top: 8, right: 24, left: 8, bottom: 0 }}>
        <CartesianGrid horizontal={false} stroke={c.grid} />
        <XAxis type="number" {...axisProps(c)} tickFormatter={(v: number) => fmt(v)} />
        <YAxis type="category" dataKey="label" {...axisProps(c)} width={170} />
        <ReferenceLine x={0} stroke={c.axis} />
        <Tooltip
          cursor={{ fill: c.grid, opacity: 0.4 }}
          contentStyle={{ background: c.surface, border: `1px solid ${c.axis}`, fontSize: 12 }}
          labelStyle={{ color: c.text }}
          formatter={(v, name, item) => {
            const d = item.payload as TornadoDatum;
            const input = name === "Input lower" ? d.lowLabel : d.highLabel;
            return [`${fmt(Number(v))} (input ${input})`, name];
          }}
        />
        <Legend wrapperStyle={{ fontSize: 12, color: c.text }} />
        <Bar dataKey="low" name="Input lower" fill={c.series[1]} radius={4} maxBarSize={14} />
        <Bar dataKey="high" name="Input higher" fill={c.series[0]} radius={4} maxBarSize={14} />
      </BarChart>
    </ResponsiveContainer>
  );
}

/** Diverging colour for a heatmap cell: blue = better than base, red = worse, grey = base. */
export function divergingColor(delta: number, maxAbs: number, c: ReturnType<typeof usePalette>) {
  if (!Number.isFinite(delta) || maxAbs === 0) return c.mid;
  const t = Math.min(1, Math.abs(delta) / maxAbs);
  const to = delta >= 0 ? c.pos : c.neg;
  return mix(c.mid, to, 0.15 + 0.75 * t);
}

function mix(a: string, b: string, t: number) {
  const pa = [1, 3, 5].map((i) => parseInt(a.slice(i, i + 2), 16));
  const pb = [1, 3, 5].map((i) => parseInt(b.slice(i, i + 2), 16));
  const r = pa.map((x, i) => Math.round(x + (pb[i] - x) * t));
  return `#${r.map((x) => x.toString(16).padStart(2, "0")).join("")}`;
}

