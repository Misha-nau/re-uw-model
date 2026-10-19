import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useDebouncedValue } from "@mantine/hooks";

import { api } from "../api/client";
import type { Inputs } from "../api/client";

/** Recalculate whenever inputs change (debounced). Keeps the last good result on screen. */
export function useUnderwrite(inputs: Inputs | null, delay = 350) {
  const [debounced] = useDebouncedValue(inputs, delay);
  return useQuery({
    queryKey: ["underwrite", debounced],
    queryFn: () => api.underwrite(debounced as Inputs),
    enabled: !!debounced,
    placeholderData: keepPreviousData,
    retry: false,
    staleTime: Infinity,
  });
}
