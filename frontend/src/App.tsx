import { Anchor, Badge, Card, Container, Group, Loader, Stack, Text, Title } from "@mantine/core";
import { useQuery } from "@tanstack/react-query";

import { api } from "./api/client";

function ApiStatus() {
  const { data, error, isPending } = useQuery({
    queryKey: ["health"],
    queryFn: api.health,
    refetchInterval: 5000,
    retry: false,
  });

  if (isPending) return <Loader size="sm" />;
  if (error)
    return (
      <Stack gap={4}>
        <Badge color="red" size="lg">API not reachable</Badge>
        <Text size="sm" c="dimmed">
          Start the backend with dev.bat, or check the backend window for errors.
        </Text>
      </Stack>
    );
  return (
    <Group gap="sm">
      <Badge color="teal" size="lg">API connected</Badge>
      <Text size="sm" c="dimmed">engine v{data.version}</Text>
    </Group>
  );
}

export default function App() {
  return (
    <Container size="sm" py="xl">
      <Stack gap="lg">
        <div>
          <Title order={2}>RE Underwriting Model</Title>
          <Text c="dimmed">Singapore office + retail acquisition underwriting</Text>
        </div>
        <Card withBorder padding="lg">
          <Stack gap="sm">
            <Text fw={600}>System status</Text>
            <ApiStatus />
            <Text size="sm">
              API docs: <Anchor href="/api/docs" target="_blank">/api/docs</Anchor>
            </Text>
          </Stack>
        </Card>
      </Stack>
    </Container>
  );
}
