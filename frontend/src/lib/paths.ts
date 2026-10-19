export type Path = (string | number)[];

export function getIn(obj: unknown, path: Path): unknown {
  let cur: unknown = obj;
  for (const k of path) {
    if (cur === null || cur === undefined) return undefined;
    cur = (cur as Record<string | number, unknown>)[k];
  }
  return cur;
}

/** Immutable set: returns a new object with ``path`` set to ``value``. */
export function setIn<T>(obj: T, path: Path, value: unknown): T {
  if (path.length === 0) return value as T;
  const [head, ...rest] = path;
  const src = (obj ?? (typeof head === "number" ? [] : {})) as Record<string | number, unknown>;
  const child = setIn(src[head], rest, value);
  if (Array.isArray(src)) {
    const copy = [...src];
    copy[head as number] = child;
    return copy as T;
  }
  return { ...src, [head]: child } as T;
}

/** Flatten nested objects/arrays to dotted paths (for scenario diffs). */
export function flatten(obj: unknown, prefix = ""): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  if (obj !== null && typeof obj === "object") {
    const entries = Array.isArray(obj)
      ? obj.map((v, i) => [String(i), v] as const)
      : Object.entries(obj as Record<string, unknown>);
    if (entries.length === 0) out[prefix] = Array.isArray(obj) ? "[]" : "{}";
    for (const [k, v] of entries) Object.assign(out, flatten(v, prefix ? `${prefix}.${k}` : k));
  } else {
    out[prefix] = obj;
  }
  return out;
}

export function deepEqual(a: unknown, b: unknown): boolean {
  return JSON.stringify(a) === JSON.stringify(b);
}
