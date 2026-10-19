export type Kind = "money" | "pct" | "ratio" | "psf" | "num";
export type Scale = "m" | "k" | "1";

export const SCALE_DIVISOR: Record<Scale, number> = { m: 1e6, k: 1e3, "1": 1 };
export const SCALE_LABEL: Record<Scale, string> = { m: "millions", k: "thousands", "1": "units" };

const nf = (digits: number) =>
  new Intl.NumberFormat("en-SG", { minimumFractionDigits: digits, maximumFractionDigits: digits });

/** Accounting style: negatives in parentheses, zero as an en dash. */
export function fmtNumber(v: number | null | undefined, digits = 2): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "n/a";
  const r = Number(v.toFixed(digits));
  if (r === 0) return "–";
  const s = nf(digits).format(Math.abs(r));
  return r < 0 ? `(${s})` : s;
}

export function fmtMoney(v: number | null | undefined, scale: Scale = "m"): string {
  const digits = scale === "1" ? 0 : scale === "k" ? 0 : 2;
  return fmtNumber(v === null || v === undefined ? v : v / SCALE_DIVISOR[scale], digits);
}

export function fmtPct(v: number | null | undefined, digits = 2): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "n/a";
  return `${(v * 100).toFixed(digits)}%`;
}

export function fmtRatio(v: number | null | undefined): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "n/a";
  return `${v.toFixed(2)}x`;
}

export function fmtValue(v: number | null | undefined, kind: Kind, scale: Scale = "m"): string {
  switch (kind) {
    case "money":
      return fmtMoney(v, scale);
    case "pct":
      return fmtPct(v);
    case "ratio":
      return fmtRatio(v);
    case "psf":
      return fmtNumber(v, 2);
    default:
      return fmtNumber(v, 2);
  }
}

/** Headline metric formatting (KPI tiles, compare table). */
export function fmtMetric(
  v: number | null | undefined,
  format: "money" | "pct" | "ratio" | "psf",
  currency = "SGD",
): string {
  if (v === null || v === undefined) return "n/a";
  if (format === "pct") return fmtPct(v);
  if (format === "ratio") return fmtRatio(v);
  const pre = currency ? `${currency} ` : "";
  if (format === "psf") return `${pre}${nf(0).format(v)}`;
  const m = fmtNumber(v / 1e6, 1);
  return `${pre}${m === "–" ? "0.0" : m}m`;
}

/** Format a sensitivity / parameter input value by unit. */
export function fmtInput(v: number, unit: string): string {
  if (unit === "pct") return fmtPct(v, 2);
  if (unit === "money") return `${fmtNumber(v / 1e6, 1)}m`;
  if (unit === "psf") return nf(2).format(v);
  return nf(2).format(v);
}
