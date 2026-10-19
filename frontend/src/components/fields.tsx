import { NumberInput, Select, SimpleGrid, Switch, Text, TextInput } from "@mantine/core";

import { getIn } from "../lib/paths";
import type { Path } from "../lib/paths";
import { useScenario } from "../state/ScenarioContext";

type NumKind = "pct" | "money" | "psf" | "num" | "int" | "ratio" | "months" | "years";

const clean = (x: number) => Number(x.toFixed(10));

interface NumFieldProps {
  path: Path;
  label: string;
  kind?: NumKind;
  nullable?: boolean;
  description?: string;
  placeholder?: string;
  min?: number;
  max?: number;
}

/** Numeric input bound to ``path``. Percentages are stored as fractions, shown as %. */
export function NumField({ path, label, kind = "num", nullable, description, placeholder,
  min, max }: NumFieldProps) {
  const { inputs, setField } = useScenario();
  const raw = getIn(inputs, path) as number | null | undefined;
  const scale = kind === "pct" ? 100 : 1;
  const value = raw === null || raw === undefined ? "" : clean(raw * scale);
  const decimals = { pct: 3, money: 0, psf: 2, num: 4, int: 0, ratio: 2, months: 2, years: 1 }[kind];
  const step = { pct: 0.25, money: 1_000_000, psf: 0.1, num: 0.1, int: 1, ratio: 0.05, months: 0.5,
    years: 0.5 }[kind];
  return (
    <NumberInput
      size="xs"
      label={label}
      description={description}
      placeholder={placeholder ?? (nullable ? "not set" : undefined)}
      value={value}
      decimalScale={decimals}
      step={step}
      min={min}
      max={max}
      thousandSeparator={kind === "money" ? "," : undefined}
      prefix={kind === "money" || kind === "psf" ? "$ " : undefined}
      suffix={kind === "pct" ? "%" : kind === "ratio" ? "x" : undefined}
      allowDecimal={kind !== "int"}
      onChange={(v) => {
        if (v === "" || v === null) {
          if (nullable) setField(path, null);
          return;
        }
        const n = typeof v === "number" ? v : Number.parseFloat(v);
        if (!Number.isNaN(n)) setField(path, kind === "int" ? Math.round(n) : clean(n / scale));
      }}
    />
  );
}

export function TextField({ path, label }: { path: Path; label: string }) {
  const { inputs, setField } = useScenario();
  return (
    <TextInput
      size="xs"
      label={label}
      value={(getIn(inputs, path) as string) ?? ""}
      onChange={(e) => setField(path, e.currentTarget.value)}
    />
  );
}

export function SelectField({ path, label, data }: {
  path: Path; label: string; data: { value: string; label: string }[];
}) {
  const { inputs, setField } = useScenario();
  return (
    <Select
      size="xs"
      label={label}
      data={data}
      allowDeselect={false}
      value={(getIn(inputs, path) as string) ?? null}
      onChange={(v) => v && setField(path, v)}
    />
  );
}

export function SwitchField({ path, label }: { path: Path; label: string }) {
  const { inputs, setField } = useScenario();
  return (
    <Switch
      size="sm"
      label={label}
      checked={Boolean(getIn(inputs, path))}
      onChange={(e) => setField(path, e.currentTarget.checked)}
    />
  );
}

/** Per-year override editor. Blank = use the flat assumption (shown as placeholder). */
export function YearOverrides({ path, label, years, fallback, kind = "pct", firstYear = 1 }: {
  path: Path;
  label: string;
  years: number;
  fallback: number;
  kind?: "pct" | "money";
  firstYear?: number;
}) {
  const { inputs, setField } = useScenario();
  const dict = (getIn(inputs, path) as Record<string, number> | undefined) ?? {};
  const scale = kind === "pct" ? 100 : 1;
  const set = (year: number, v: number | string) => {
    const next = { ...dict };
    if (v === "" || v === null) delete next[String(year)];
    else {
      const n = typeof v === "number" ? v : Number.parseFloat(v);
      if (Number.isNaN(n)) return;
      next[String(year)] = clean(n / scale);
    }
    setField(path, next);
  };
  const ys = Array.from({ length: years - firstYear + 1 }, (_, i) => firstYear + i);
  return (
    <div>
      <Text size="xs" fw={500} mb={4}>{label}</Text>
      <SimpleGrid cols={Math.min(ys.length, 6)} spacing={4} verticalSpacing={4}>
        {ys.map((y) => {
          const v = dict[String(y)];
          return (
            <NumberInput
              key={y}
              size="xs"
              aria-label={`${label} year ${y}`}
              leftSection={<Text size="10px" c="dimmed">Y{y}</Text>}
              leftSectionWidth={26}
              hideControls
              placeholder={kind === "pct" ? `${clean(fallback * 100)}%` : String(fallback)}
              value={v === undefined ? "" : clean(v * scale)}
              decimalScale={kind === "pct" ? 3 : 0}
              thousandSeparator={kind === "money" ? "," : undefined}
              suffix={kind === "pct" ? "%" : undefined}
              onChange={(val) => set(y, val)}
            />
          );
        })}
      </SimpleGrid>
    </div>
  );
}
