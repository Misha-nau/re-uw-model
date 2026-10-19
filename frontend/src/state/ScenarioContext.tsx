import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { notifications } from "@mantine/notifications";

import { api, ApiError } from "../api/client";
import type { Inputs, ScenarioSummary } from "../api/client";
import { deepEqual, setIn } from "../lib/paths";
import type { Path } from "../lib/paths";

const DEFAULT_ID = "sample_sg_cbd_office_retail";
const LAST_KEY = "re-uw:last-scenario";

function readLast(): string | null {
  try {
    return localStorage.getItem(LAST_KEY);
  } catch {
    return null;
  }
}
function writeLast(id: string | null) {
  try {
    if (id) localStorage.setItem(LAST_KEY, id);
    else localStorage.removeItem(LAST_KEY);
  } catch {
    /* storage unavailable */
  }
}

interface ScenarioState {
  scenarios: ScenarioSummary[];
  scenarioId: string | null;
  inputs: Inputs | null;
  saved: Inputs | null;
  dirty: boolean;
  busy: boolean;
  setField: (path: Path, value: unknown) => void;
  update: (fn: (prev: Inputs) => Inputs) => void;
  load: (id: string) => Promise<void>;
  save: () => Promise<void>;
  saveAs: (name: string) => Promise<void>;
  remove: () => Promise<void>;
  reset: () => void;
}

const Ctx = createContext<ScenarioState | null>(null);

function notifyError(title: string, e: unknown) {
  const msg = e instanceof ApiError ? [e.message, ...e.details].join("\n") : String(e);
  notifications.show({ color: "red", title, message: msg });
}

export function ScenarioProvider({ children }: { children: ReactNode }) {
  const qc = useQueryClient();
  const list = useQuery({ queryKey: ["scenarios"], queryFn: api.listScenarios });
  const [scenarioId, setScenarioId] = useState<string | null>(null);
  const [inputs, setInputs] = useState<Inputs | null>(null);
  const [saved, setSaved] = useState<Inputs | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async (id: string) => {
    setBusy(true);
    try {
      const data = await api.getScenario(id);
      setScenarioId(id);
      setInputs(data);
      setSaved(data);
      writeLast(id);
    } catch (e) {
      notifyError("Could not load scenario", e);
    } finally {
      setBusy(false);
    }
  }, []);

  // First load: last-used scenario, else the sample, else the first available.
  useEffect(() => {
    if (inputs || !list.data || list.data.length === 0) return;
    const ids = list.data.map((s) => s.id);
    const last = readLast();
    const id = last && ids.includes(last) ? last : ids.includes(DEFAULT_ID) ? DEFAULT_ID : ids[0];
    void load(id);
  }, [list.data, inputs, load]);

  const setField = useCallback((path: Path, value: unknown) => {
    setInputs((prev) => (prev ? setIn(prev, path, value) : prev));
  }, []);
  const update = useCallback((fn: (prev: Inputs) => Inputs) => {
    setInputs((prev) => (prev ? fn(prev) : prev));
  }, []);

  const refreshList = () => qc.invalidateQueries({ queryKey: ["scenarios"] });

  const save = useCallback(async () => {
    if (!inputs || !scenarioId) return;
    setBusy(true);
    try {
      await api.saveScenario(scenarioId, inputs);
      setSaved(inputs);
      await refreshList();
      notifications.show({ color: "teal", message: `Saved "${inputs.scenario.name}"` });
    } catch (e) {
      notifyError("Save failed", e);
    } finally {
      setBusy(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [inputs, scenarioId]);

  const saveAs = useCallback(async (name: string) => {
    if (!inputs) return;
    setBusy(true);
    try {
      const next = setIn(inputs, ["scenario", "name"], name);
      const created = await api.createScenario(next);
      setScenarioId(created.id);
      setInputs(next);
      setSaved(next);
      writeLast(created.id);
      await refreshList();
      notifications.show({ color: "teal", message: `Saved as "${name}"` });
    } catch (e) {
      notifyError("Save as failed", e);
    } finally {
      setBusy(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [inputs]);

  const remove = useCallback(async () => {
    if (!scenarioId) return;
    setBusy(true);
    try {
      await api.deleteScenario(scenarioId);
      const remaining = (await api.listScenarios()).filter((s) => s.id !== scenarioId);
      await refreshList();
      writeLast(null);
      setInputs(null);
      setSaved(null);
      setScenarioId(null);
      if (remaining.length) await load(remaining[0].id);
      notifications.show({ color: "gray", message: "Scenario deleted" });
    } catch (e) {
      notifyError("Delete failed", e);
    } finally {
      setBusy(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scenarioId, load]);

  const reset = useCallback(() => setInputs(saved), [saved]);

  const value = useMemo<ScenarioState>(
    () => ({
      scenarios: list.data ?? [],
      scenarioId,
      inputs,
      saved,
      dirty: !!inputs && !!saved && !deepEqual(inputs, saved),
      busy,
      setField,
      update,
      load,
      save,
      saveAs,
      remove,
      reset,
    }),
    [list.data, scenarioId, inputs, saved, busy, setField, update, load, save, saveAs, remove, reset],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useScenario(): ScenarioState {
  const v = useContext(Ctx);
  if (!v) throw new Error("useScenario must be used inside ScenarioProvider");
  return v;
}

/** The working inputs, asserted non-null (use under a loaded guard). */
export function useInputs(): Inputs {
  const { inputs } = useScenario();
  if (!inputs) throw new Error("no scenario loaded");
  return inputs;
}
