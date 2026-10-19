import { useEffect, useState } from "react";
import { ActionIcon, AppShell, Badge, Button, Center, Group, Loader, ScrollArea, Stack, Text,
  Title, Tooltip, useMantineColorScheme } from "@mantine/core";
import { useQuery } from "@tanstack/react-query";

import { api } from "./api/client";
import { ScenarioBar } from "./components/ScenarioBar";
import { ComparePage } from "./pages/ComparePage";
import { SensitivityPage } from "./pages/SensitivityPage";
import { UnderwritingPage } from "./pages/UnderwritingPage";
import { useScenario } from "./state/ScenarioContext";

type Page = "underwriting" | "compare" | "sensitivity";
const PAGES: { value: Page; label: string }[] = [
  { value: "underwriting", label: "Underwriting" },
  { value: "compare", label: "Compare" },
  { value: "sensitivity", label: "Sensitivity" },
];

function pageFromHash(): Page {
  const h = window.location.hash.replace("#", "");
  return (PAGES.find((p) => p.value === h)?.value ?? "underwriting") as Page;
}

function ApiDown() {
  return (
    <Center h="60vh">
      <Stack align="center" gap="xs">
        <Badge color="red" size="lg">API not reachable</Badge>
        <Text size="sm" c="dimmed">Start the backend with dev.bat, or check the "RE UW - API" window.</Text>
      </Stack>
    </Center>
  );
}

export default function App() {
  const [page, setPage] = useState<Page>(pageFromHash);
  const { inputs } = useScenario();
  const { colorScheme, toggleColorScheme } = useMantineColorScheme();
  const health = useQuery({ queryKey: ["health"], queryFn: api.health, retry: 1,
    refetchInterval: 15000 });

  useEffect(() => {
    const onHash = () => setPage(pageFromHash());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);
  const go = (p: Page) => {
    window.location.hash = p;
    setPage(p);
  };

  return (
    <AppShell header={{ height: 96 }} padding="md">
      <AppShell.Header px="md">
        <Group h={48} justify="space-between" wrap="nowrap">
          <Group gap="lg" wrap="nowrap">
            <Title order={4} style={{ whiteSpace: "nowrap" }}>RE Underwriting Model</Title>
            <Group gap={4}>
              {PAGES.map((p) => (
                <Button key={p.value} size="xs" variant={page === p.value ? "filled" : "subtle"}
                  onClick={() => go(p.value)}>{p.label}</Button>
              ))}
            </Group>
          </Group>
          <Group gap="xs" wrap="nowrap">
            <Text size="xs" c="dimmed">
              {health.data ? `engine v${health.data.version}` : health.isError ? "API offline" : ""}
            </Text>
            <Tooltip label="Toggle light / dark">
              <ActionIcon variant="default" onClick={toggleColorScheme} aria-label="Toggle colour scheme">
                {colorScheme === "dark" ? "☀" : "☾"}
              </ActionIcon>
            </Tooltip>
          </Group>
        </Group>
        <ScrollArea type="never">
          <Group h={44}><ScenarioBar /></Group>
        </ScrollArea>
      </AppShell.Header>
      <AppShell.Main>
        {health.isError ? <ApiDown /> : !inputs ? <Center h="50vh"><Loader /></Center> : (
          <>
            {page === "underwriting" && <UnderwritingPage />}
            {page === "compare" && <ComparePage />}
            {page === "sensitivity" && <SensitivityPage />}
          </>
        )}
      </AppShell.Main>
    </AppShell>
  );
}
