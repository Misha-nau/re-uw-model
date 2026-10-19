// Minimal API client. In Phase 6 the types here are replaced by types
// generated from FastAPI's OpenAPI spec (openapi-typescript).

export interface Health {
  status: string;
  version: string;
}

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return (await res.json()) as T;
}

export const api = {
  health: () => getJson<Health>("/api/health"),
};
