import { describe, expect, it } from "vitest";

import { fmtMetric, fmtMoney, fmtNumber, fmtPct } from "./format";
import { flatten, getIn, setIn } from "./paths";

describe("format", () => {
  it("uses accounting style", () => {
    expect(fmtNumber(-1234.5, 1)).toBe("(1,234.5)");
    expect(fmtNumber(0)).toBe("–");
    expect(fmtNumber(null)).toBe("n/a");
  });
  it("scales money", () => {
    expect(fmtMoney(32_631_130, "m")).toBe("32.63");
    expect(fmtMoney(32_631_130, "k")).toBe("32,631");
  });
  it("formats percentages and metrics", () => {
    expect(fmtPct(0.0375)).toBe("3.75%");
    expect(fmtMetric(514_494_600, "money")).toBe("SGD 514.5m");
    expect(fmtMetric(2.3654, "ratio")).toBe("2.37x");
    expect(fmtMetric(0, "money")).toBe("SGD 0.0m");
    expect(fmtMetric(-1_500_000, "money", "")).toBe("(1.5)m");
  });
});

describe("paths", () => {
  const obj = { a: { b: [{ c: 1 }, { c: 2 }] } };
  it("gets and sets immutably", () => {
    expect(getIn(obj, ["a", "b", 1, "c"])).toBe(2);
    const next = setIn(obj, ["a", "b", 0, "c"], 9);
    expect(getIn(next, ["a", "b", 0, "c"])).toBe(9);
    expect(getIn(obj, ["a", "b", 0, "c"])).toBe(1);
    expect(Array.isArray(getIn(next, ["a", "b"]))).toBe(true);
  });
  it("flattens", () => {
    expect(flatten(obj)).toEqual({ "a.b.0.c": 1, "a.b.1.c": 2 });
    expect(flatten({ x: {} })).toEqual({ x: "{}" });
  });
});
