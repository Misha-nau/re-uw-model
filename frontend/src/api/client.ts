// Typed API client. Types are generated from FastAPI's OpenAPI spec:
//   backend: python scripts/export_openapi.py   frontend: npm run gen:api
import type { components } from "./schema";

type S = components["schemas"];
export type Inputs = S["UnderwritingInputs"];
export type UnderwriteResponse = S["UnderwriteResponse"];
export type Table = S["Table"];
export type TableRow = S["TableRow"];
export type ScenarioSummary = S["ScenarioSummary"];
export type MetricInfo = S["MetricInfo"];
export type ParameterInfo = S["ParameterInfo"];
export type SensitivityResponse = S["SensitivityResponse"];
export type TornadoResponse = S["TornadoResponse"];
export interface Health {
  status: string;
  version: string;
}

export class ApiError extends Error {
  status: number;
  details: string[];
  constructor(status: number, message: string, details: string[] = []) {
    super(message);
    this.status = status;
    this.details = details;
  }
}

interface ValidationDetail {
  loc: (string | number)[];
  msg: string;
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(path, {
    method,
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!res.ok) {
    let message = `${res.status} ${res.statusText}`;
    let details: string[] = [];
    try {
      const data = await res.json();
      if (typeof data.detail === "string") message = data.detail;
      else if (Array.isArray(data.detail)) {
        message = "Some inputs are invalid";
        details = (data.detail as ValidationDetail[]).map(
          (d) => `${d.loc.filter((x) => x !== "body").join(" › ")}: ${d.msg.replace(/^Value error, /, "")}`,
        );
      }
    } catch {
      /* not JSON */
    }
    throw new ApiError(res.status, message, details);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  health: () => request<Health>("GET", "/api/health"),
  metrics: () => request<MetricInfo[]>("GET", "/api/metrics"),
  underwrite: (inputs: Inputs) => request<UnderwriteResponse>("POST", "/api/underwrite", inputs),
  listScenarios: () => request<ScenarioSummary[]>("GET", "/api/scenarios"),
  getScenario: (id: string) => request<Inputs>("GET", `/api/scenarios/${encodeURIComponent(id)}`),
  createScenario: (inputs: Inputs) =>
    request<ScenarioSummary>("POST", "/api/scenarios", { inputs }),
  saveScenario: (id: string, inputs: Inputs) =>
    request<ScenarioSummary>("PUT", `/api/scenarios/${encodeURIComponent(id)}`, inputs),
  deleteScenario: (id: string) =>
    request<void>("DELETE", `/api/scenarios/${encodeURIComponent(id)}`),
  parameters: (inputs: Inputs) =>
    request<ParameterInfo[]>("POST", "/api/sensitivity/parameters", inputs),
  sensitivity: (body: S["SensitivityRequest"]) =>
    request<SensitivityResponse>("POST", "/api/sensitivity", body),
  tornado: (body: S["TornadoRequest"]) => request<TornadoResponse>("POST", "/api/tornado", body),
  async exportXlsx(inputs: Inputs): Promise<void> {
    const res = await fetch("/api/export", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(inputs),
    });
    if (!res.ok) throw new ApiError(res.status, "Export failed");
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${inputs.scenario.name.replace(/[^\w\- ]+/g, "_")}.xlsx`;
    a.click();
    URL.revokeObjectURL(url);
  },
};
