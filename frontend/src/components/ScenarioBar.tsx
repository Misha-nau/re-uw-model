import { useState } from "react";
import { Badge, Button, Group, Modal, Select, Stack, Text, TextInput, Tooltip } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { api } from "../api/client";
import { useScenario } from "../state/ScenarioContext";

type Dialog = null | { kind: "saveAs" | "duplicate" } | { kind: "switch"; target: string }
  | { kind: "delete" };

export function ScenarioBar() {
  const s = useScenario();
  const [dialog, setDialog] = useState<Dialog>(null);
  const [name, setName] = useState("");
  const close = () => setDialog(null);

  const openName = (kind: "saveAs" | "duplicate") => {
    const base = s.inputs?.scenario.name ?? "Scenario";
    setName(kind === "duplicate" ? `Copy of ${base}` : base);
    setDialog({ kind });
  };

  const switchTo = (id: string | null) => {
    if (!id || id === s.scenarioId) return;
    if (s.dirty) setDialog({ kind: "switch", target: id });
    else void s.load(id);
  };

  return (
    <Group gap="xs" wrap="nowrap" style={{ minWidth: "max-content" }}>
      <Select
        size="xs"
        w={320}
        aria-label="Scenario"
        placeholder="Select scenario"
        searchable
        data={s.scenarios.map((x) => ({ value: x.id, label: x.name }))}
        value={s.scenarioId}
        onChange={switchTo}
        allowDeselect={false}
      />
      {s.dirty ? (
        <Badge color="orange" variant="light">Unsaved changes</Badge>
      ) : (
        <Badge color="gray" variant="light">Saved</Badge>
      )}
      <Button size="xs" disabled={!s.dirty || s.busy} onClick={() => void s.save()}>Save</Button>
      <Button size="xs" variant="default" disabled={!s.inputs || s.busy}
        onClick={() => openName("saveAs")}>Save as…</Button>
      <Button size="xs" variant="default" disabled={!s.inputs || s.busy}
        onClick={() => openName("duplicate")}>Duplicate</Button>
      <Tooltip label="Discard unsaved changes">
        <Button size="xs" variant="default" disabled={!s.dirty} onClick={s.reset}>Reset</Button>
      </Tooltip>
      <Button size="xs" variant="default" disabled={!s.inputs}
        onClick={() => s.inputs && api.exportXlsx(s.inputs).catch((e) =>
          notifications.show({ color: "red", message: String(e) }))}>
        Export Excel
      </Button>
      <Button size="xs" variant="subtle" color="red" disabled={!s.scenarioId || s.busy}
        onClick={() => setDialog({ kind: "delete" })}>Delete</Button>

      <Modal opened={dialog?.kind === "saveAs" || dialog?.kind === "duplicate"} onClose={close}
        title={dialog?.kind === "duplicate" ? "Duplicate scenario" : "Save as new scenario"}>
        <Stack>
          <TextInput label="Scenario name" value={name} data-autofocus
            onChange={(e) => setName(e.currentTarget.value)} />
          {dialog?.kind === "duplicate" && (
            <Text size="xs" c="dimmed">Saves a copy of the current inputs (including unsaved edits)
              under a new name and switches to it.</Text>
          )}
          <Group justify="flex-end">
            <Button variant="default" onClick={close}>Cancel</Button>
            <Button disabled={!name.trim()} onClick={async () => {
              close();
              await s.saveAs(name.trim());
            }}>Save</Button>
          </Group>
        </Stack>
      </Modal>

      <Modal opened={dialog?.kind === "switch"} onClose={close} title="Discard unsaved changes?">
        <Stack>
          <Text size="sm">You have unsaved changes to "{s.inputs?.scenario.name}".</Text>
          <Group justify="flex-end">
            <Button variant="default" onClick={close}>Keep editing</Button>
            <Button color="orange" onClick={() => {
              if (dialog?.kind === "switch") void s.load(dialog.target);
              close();
            }}>Discard and switch</Button>
          </Group>
        </Stack>
      </Modal>

      <Modal opened={dialog?.kind === "delete"} onClose={close} title="Delete scenario?">
        <Stack>
          <Text size="sm">"{s.saved?.scenario.name}" will be deleted from the scenarios folder.
            This cannot be undone (unless you restore it from Git).</Text>
          <Group justify="flex-end">
            <Button variant="default" onClick={close}>Cancel</Button>
            <Button color="red" onClick={() => { close(); void s.remove(); }}>Delete</Button>
          </Group>
        </Stack>
      </Modal>
    </Group>
  );
}
